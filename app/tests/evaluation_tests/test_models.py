from collections import namedtuple
from datetime import timedelta
from itertools import chain

import pytest
from django.utils import timezone
from django.utils.timezone import now

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.tasks import (
    calculate_ranks,
    create_evaluation,
    update_combined_leaderboard,
)
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    CombinedLeaderboardFactory,
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory, ImageFactory, UserFactory


@pytest.fixture
def algorithm_submission():
    algorithm_submission = namedtuple(
        "algorithm_submission", ["method", "algorithm_image", "images"]
    )

    method = MethodFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        phase__archive=ArchiveFactory(),
    )
    algorithm_image = AlgorithmImageFactory()

    interface = ComponentInterfaceFactory()
    algorithm_image.algorithm.inputs.set([interface])

    images = ImageFactory.create_batch(3)

    for image in images[:2]:
        civ = ComponentInterfaceValueFactory(image=image, interface=interface)
        ai = ArchiveItemFactory(archive=method.phase.archive)
        ai.values.add(civ)

    return algorithm_submission(
        method=method, algorithm_image=algorithm_image, images=images
    )


@pytest.mark.django_db
def test_algorithm_submission_creates_one_job_per_test_set_image(
    django_capture_on_commit_callbacks, settings, algorithm_submission
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s = SubmissionFactory(
        phase=algorithm_submission.method.phase,
        algorithm_image=algorithm_submission.algorithm_image,
    )

    with django_capture_on_commit_callbacks() as callbacks:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    # Execute the callbacks non-recursively
    for c in callbacks:
        c()

    assert Job.objects.count() == 2
    assert [
        inpt.image for ae in Job.objects.all() for inpt in ae.inputs.all()
    ] == algorithm_submission.images[:2]


@pytest.mark.django_db
def test_create_evaluation_is_idempotent(
    django_capture_on_commit_callbacks, settings, algorithm_submission
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s = SubmissionFactory(
        phase=algorithm_submission.method.phase,
        algorithm_image=algorithm_submission.algorithm_image,
    )

    with django_capture_on_commit_callbacks(execute=False) as callbacks1:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    with django_capture_on_commit_callbacks(execute=False) as callbacks2:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    # Execute the callbacks non-recursively
    for c in chain(callbacks1, callbacks2):
        c()

    assert Job.objects.count() == 2


@pytest.mark.django_db
class TestPhaseLimits:
    def setup_method(self):
        self.phase = PhaseFactory()
        self.user = UserFactory()
        evaluation_kwargs = {
            "submission__creator": self.user,
            "submission__phase": self.phase,
            "status": Evaluation.SUCCESS,
        }
        now = timezone.now()

        # Failed evaluations don't count
        e = EvaluationFactory(
            submission__creator=self.user,
            submission__phase=self.phase,
            status=Evaluation.FAILURE,
        )
        # Other users evaluations don't count
        EvaluationFactory(
            submission__creator=UserFactory(),
            submission__phase=self.phase,
            status=Evaluation.SUCCESS,
        )
        # Other phases don't count
        EvaluationFactory(
            submission__creator=self.user,
            submission__phase=PhaseFactory(),
            status=Evaluation.SUCCESS,
        )

        # Evaluations 1, 2 and 7 days ago
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=1) + timedelta(hours=1)
        e.submission.save()
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=2) + timedelta(hours=1)
        e.submission.save()
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=7) + timedelta(hours=1)
        e.submission.save()

    @pytest.mark.parametrize("submission_limit_period", (None, 1, 3))
    def test_submissions_closed(self, submission_limit_period):
        self.phase.submissions_limit_per_user_per_period = 0
        self.phase.submission_limit_period = submission_limit_period

        i = self.phase.get_next_submission(user=UserFactory())

        assert i["remaining_submissions"] == 0
        assert i["next_submission_at"] is None

    @pytest.mark.parametrize(
        "submission_limit_period,expected_remaining", ((1, 2), (3, 1), (28, 0))
    )
    def test_submissions_period(
        self, submission_limit_period, expected_remaining
    ):
        self.phase.submissions_limit_per_user_per_period = (
            3  # successful jobs created in setUp
        )
        self.phase.submission_limit_period = submission_limit_period

        i = self.phase.get_next_submission(user=self.user)

        assert i["remaining_submissions"] == expected_remaining
        assert i["next_submission_at"] is not None

    @pytest.mark.parametrize(
        "submissions_limit_per_user_per_period,expected_remaining",
        ((4, 1), (3, 0), (1, 0)),
    )
    def test_submissions_period_none(
        self, submissions_limit_per_user_per_period, expected_remaining
    ):
        self.phase.submissions_limit_per_user_per_period = (
            submissions_limit_per_user_per_period
        )
        self.phase.submission_limit_period = None

        i = self.phase.get_next_submission(user=self.user)

        assert i["remaining_submissions"] == expected_remaining
        if expected_remaining > 0:
            assert i["next_submission_at"] is not None
        else:
            assert i["next_submission_at"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "submissions_limit_per_user_per_period,submissions_open,submissions_close,submissions_limit,open_for_submissions,expected_status",
    [
        (0, None, None, 10, False, "Not accepting submissions"),
        (
            0,
            now() - timedelta(days=1),
            None,
            10,
            False,
            "Not accepting submissions",
        ),
        (
            0,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            10,
            False,
            "completed",
        ),
        (
            0,
            now() - timedelta(days=10),
            now() + timedelta(days=1),
            10,
            False,
            "Not accepting submissions",
        ),
        (
            0,
            now() + timedelta(days=10),
            None,
            10,
            False,
            "Opening submissions",
        ),
        (
            0,
            now() + timedelta(days=10),
            now() + timedelta(days=15),
            10,
            False,
            "Opening submissions",
        ),
        (0, None, now() - timedelta(days=15), 10, False, "completed"),
        (
            0,
            None,
            now() + timedelta(days=15),
            10,
            False,
            "Not accepting submissions",
        ),
        (10, None, None, 10, True, "Accepting submissions"),
        (
            10,
            now() - timedelta(days=1),
            None,
            10,
            True,
            "Accepting submissions",
        ),
        (
            10,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            10,
            False,
            "completed",
        ),
        (
            10,
            now() - timedelta(days=10),
            now() + timedelta(days=1),
            10,
            True,
            "Accepting submissions",
        ),
        (
            10,
            now() + timedelta(days=10),
            None,
            10,
            False,
            "Opening submissions",
        ),
        (
            10,
            now() + timedelta(days=10),
            now() + timedelta(days=15),
            10,
            False,
            "Opening submissions",
        ),
        (10, None, None, 1, False, "Not accepting submissions"),
        (10, None, None, None, True, "Accepting submissions"),
    ],
)
def test_open_for_submission(
    submissions_limit_per_user_per_period,
    submissions_open,
    submissions_close,
    submissions_limit,
    open_for_submissions,
    expected_status,
):
    phase = PhaseFactory()
    phase.submissions_limit_per_user_per_period = (
        submissions_limit_per_user_per_period
    )
    phase.submissions_open_at = submissions_open
    phase.submissions_close_at = submissions_close
    phase.total_number_of_submissions_allowed = submissions_limit
    phase.save()

    SubmissionFactory.create_batch(5, phase=phase)

    assert phase.open_for_submissions == open_for_submissions
    assert expected_status in phase.submission_status_string


@pytest.mark.django_db
def test_combined_leaderboards(
    django_capture_on_commit_callbacks, django_assert_max_num_queries
):
    challenge = ChallengeFactory()
    phases = PhaseFactory.create_batch(
        2,
        challenge=challenge,
        score_jsonpath="result",
        score_default_sort="asc",
    )
    users = UserFactory.create_batch(3)
    leaderboard = CombinedLeaderboardFactory(challenge=challenge)
    leaderboard.phases.set(challenge.phase_set.all())
    interface = ComponentInterface.objects.get(slug="metrics-json-file")

    results = {
        0: {
            0: (1, 2),
            1: (1, 2),
        },
        1: {
            0: (3, 3),
            1: (2, 3),
        },
        2: {
            0: (2, 3),
            1: (2, 3),
        },
    }

    for phase_idx, phase in enumerate(phases):
        for user_idx, user in enumerate(users):
            for result in results[user_idx][phase_idx]:
                evaluation = EvaluationFactory(
                    submission__creator=user,
                    submission__phase=phase,
                    published=True,
                    status=Evaluation.SUCCESS,
                )

                output_civ, _ = evaluation.outputs.get_or_create(
                    interface=interface
                )
                output_civ.value = {"result": result}
                output_civ.save()

        with django_capture_on_commit_callbacks() as callbacks:
            calculate_ranks(phase_pk=phase.pk)

        assert len(callbacks) == 1
        assert (
            repr(callbacks[0])
            == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
        )

    with django_assert_max_num_queries(6):
        update_combined_leaderboard(pk=leaderboard.pk)

    assert (
        Evaluation.objects.filter(
            submission__phase__challenge=challenge
        ).count()
        == 12
    )
    assert (
        Evaluation.objects.filter(
            submission__phase__challenge=challenge, rank=1
        ).count()
        == 2
    )

    ranks = leaderboard.combined_ranks

    assert ranks[0]["combined_rank"] == 1
    assert ranks[0]["user"] == users[0].username
    assert ranks[1]["combined_rank"] == 2
    assert ranks[1]["user"] == users[2].username
    assert ranks[2]["combined_rank"] == 3
    assert ranks[2]["user"] == users[1].username


@pytest.mark.django_db
def test_combined_leaderboard_updated_on_save(
    django_capture_on_commit_callbacks,
):
    leaderboard = CombinedLeaderboardFactory()

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.save()

    assert len(callbacks) == 1
    assert (
        repr(callbacks[0])
        == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
    )


@pytest.mark.django_db
def test_combined_leaderboard_updated_on_phase_change(
    django_capture_on_commit_callbacks,
):
    leaderboard = CombinedLeaderboardFactory()
    phase = PhaseFactory()

    def assert_callbacks(callbacks):
        assert len(callbacks) == 1
        assert (
            repr(callbacks[0])
            == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
        )

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.add(phase)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.remove(phase)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.set([phase])

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.clear()

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.add(leaderboard)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.remove(leaderboard)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.set([leaderboard])

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.clear()

    assert_callbacks(callbacks)

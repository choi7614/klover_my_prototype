"""F4 첫 단계: 메일 조회·제외·업무 그룹 구성. 보고서 문장은 생성하지 않는다."""

from app.db.repositories.report_mail import ReportMailRepository
from app.schemas.report import (
    ExcludedReportMail,
    ReportMail,
    ReportMailGroup,
    ReportPeriod,
    WeeklyReportInput,
)


class ReportInputNotReadyError(ValueError):
    def __init__(self, mail_ids: tuple[str, ...]) -> None:
        self.mail_ids = mail_ids
        super().__init__(f"업무 메일 {len(mail_ids)}건의 분석이 완료되지 않았습니다")


def _group_mails(mails: list[ReportMail]) -> tuple[ReportMailGroup, ...]:
    # 같은 스레드 또는 프로젝트로 이어지는 메일의 연결 성분을 구한다.
    parents = list(range(len(mails)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen: dict[tuple[str, str], int] = {}
    for index, mail in enumerate(mails):
        keys = {
            ("project", project.strip()) for project in mail.entities.projects if project.strip()
        }
        if mail.thread_id and mail.thread_id.strip():
            keys.add(("thread", mail.thread_id.strip()))
        for key in sorted(keys):
            previous = seen.setdefault(key, index)
            parents[find(index)] = find(previous)

    components: dict[int, list[ReportMail]] = {}
    for index, mail in enumerate(mails):
        components.setdefault(find(index), []).append(mail)

    return tuple(
        ReportMailGroup(group_id=f"group_{index:03d}", mails=tuple(group))
        for index, group in enumerate(components.values(), start=1)
    )


async def prepare_weekly_report_input(
    *, repository: ReportMailRepository, user_id: str, period: ReportPeriod
) -> WeeklyReportInput:
    if not user_id.strip():
        raise ValueError("사용자 ID가 필요합니다")

    mails = sorted(
        await repository.list_received_and_sent(
            user_id=user_id, start_at=period.start_at, end_before=period.end_before
        ),
        key=lambda mail: (mail.received_at, mail.mail_id),
    )
    if len({mail.mail_id for mail in mails}) != len(mails) or any(
        mail.user_id != user_id or not period.start_at <= mail.received_at < period.end_before
        for mail in mails
    ):
        raise ValueError("메일 저장소가 사용자·기간·중복 조회 계약을 위반했습니다")

    included: list[ReportMail] = []
    excluded: list[ExcludedReportMail] = []
    not_ready: list[str] = []
    for mail in mails:
        category = mail.effective_category
        if category in ("notice", "newsletter"):
            excluded.append(ExcludedReportMail(mail=mail, reason=category))
        elif mail.analysis_status != "done" or category is None:
            not_ready.append(mail.mail_id)
        else:
            included.append(mail)

    if not_ready:
        raise ReportInputNotReadyError(tuple(not_ready))

    return WeeklyReportInput(period=period, groups=_group_mails(included), excluded=tuple(excluded))

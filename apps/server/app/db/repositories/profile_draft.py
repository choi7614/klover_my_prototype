"""F2 저장소. 소유자·버전 조건으로 다른 사용자와 오래된 편집의 덮어쓰기를 막는다."""

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.f2_port import F2Error
from app.db.f2_models import DraftRecord, ProfileRecord, StyleRecord
from app.schemas.profile_draft import DraftState, Profile, ProfileState, ProfileUpdate, StyleState


def conflict():
    return F2Error("version_conflict", 409, "다른 변경이 저장됐어요. 다시 불러온 뒤 확인해 주세요.")


class F2Repository:
    def __init__(self, engine):
        self.engine = engine

    def profile(self, *, user_id: str) -> ProfileState:
        with Session(self.engine) as session:
            row = session.get(ProfileRecord, user_id)
            return self._profile(row)

    def report_profile(self, *, user_id: str) -> ProfileState:
        """F4 읽기 포트. user_id는 F4 서버 인증 문맥에서만 전달한다."""
        return self.profile(user_id=user_id)

    @staticmethod
    def _profile(row):
        if row is None:
            return ProfileState()
        return ProfileState(
            profile=Profile.model_validate(
                {key: getattr(row, key) for key in Profile.model_fields}
            ),
            exists=True,
            version=row.version,
        )

    def save_profile(self, *, user_id: str, request: ProfileUpdate) -> ProfileState:
        try:
            with Session(self.engine) as session, session.begin():
                row = session.get(ProfileRecord, user_id)
                previous = self._profile(row)
                if previous.version != request.expected_version:
                    raise conflict()
                if (
                    request.profile.style_learning_enabled
                    and not previous.profile.style_learning_enabled
                    and not request.consent_given
                ):
                    raise F2Error(
                        "consent_required", 422, "문체 학습에 먼저 명시적으로 동의해 주세요."
                    )
                version = previous.version + 1
                values = dict(**request.profile.model_dump(mode="json"), version=version)
                if row is None:
                    session.add(ProfileRecord(user_id=user_id, **values))
                    session.flush()
                else:
                    changed = session.execute(
                        update(ProfileRecord)
                        .where(
                            ProfileRecord.user_id == user_id,
                            ProfileRecord.version == request.expected_version,
                        )
                        .values(**values)
                    )
                    if changed.rowcount != 1:
                        raise conflict()
                return ProfileState(profile=request.profile, exists=True, version=version)
        except IntegrityError:
            raise conflict() from None

    def style(self, *, user_id: str, profile: Profile | None = None) -> StyleState:
        profile = profile or self.profile(user_id=user_id).profile
        if not profile.style_learning_enabled:
            return StyleState()
        with Session(self.engine) as session:
            row = session.get(StyleRecord, user_id)
            if row is None:
                return StyleState(enabled=True, status="unavailable")
            stored = StyleState.model_validate(row.payload)
            return StyleState(
                enabled=True,
                status="ready" if stored.analyzed_count else "unavailable",
                analyzed_count=stored.analyzed_count,
                phrases=tuple(p for p in stored.phrases if p not in profile.excluded_phrases),
                traits=stored.traits,
            )

    def delete_style(self, *, user_id: str) -> ProfileState:
        with Session(self.engine) as session, session.begin():
            row = session.scalar(
                select(ProfileRecord).where(ProfileRecord.user_id == user_id).with_for_update()
            )
            session.execute(delete(StyleRecord).where(StyleRecord.user_id == user_id))
            if row is None:
                return ProfileState()
            profile = self._profile(row).profile.model_copy(
                update={"style_learning_enabled": False, "excluded_phrases": ()}
            )
            for key, value in profile.model_dump(mode="json").items():
                setattr(row, key, value)
            row.version += 1
            return ProfileState(profile=profile, exists=True, version=row.version)

    def draft(self, *, user_id: str, draft_id: str) -> DraftState:
        with Session(self.engine) as session:
            row = session.scalar(
                select(DraftRecord).where(
                    DraftRecord.user_id == user_id, DraftRecord.draft_id == draft_id
                )
            )
            if row is None:
                raise F2Error("not_found", 404, "초안을 찾을 수 없습니다.")
            return DraftState.model_validate(row.payload)

    def save_draft(
        self, *, user_id: str, draft: DraftState, expected_version: int | None = None
    ) -> DraftState:
        with Session(self.engine) as session, session.begin():
            values = dict(payload=draft.model_dump(mode="json"), version=draft.version)
            if expected_version is None:
                session.add(DraftRecord(user_id=user_id, draft_id=draft.draft_id, **values))
            else:
                changed = session.execute(
                    update(DraftRecord)
                    .where(
                        DraftRecord.user_id == user_id,
                        DraftRecord.draft_id == draft.draft_id,
                        DraftRecord.version == expected_version,
                    )
                    .values(**values)
                )
                if changed.rowcount != 1:
                    raise conflict()
        return draft

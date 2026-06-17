from app.spaces import space_repository
from app.spaces.schemas import SpaceIn


def list_spaces():
    return space_repository.list_all()


def create_space(payload: SpaceIn):
    return space_repository.create(
        payload.model_dump(exclude={"member_ids"}), payload.member_ids
    )


def update_space(space_id, payload: SpaceIn):
    return space_repository.update(
        space_id, payload.model_dump(exclude={"member_ids"}), payload.member_ids
    )


def delete_space(space_id):
    return space_repository.delete(space_id)
from app.models.card import Card
from app.models.user import User, UserRole

STAFF_ROLES = {UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VENDEDOR}


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def can_manage_cards(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.SUPERVISOR}


def owns_card(user: User, card: Card) -> bool:
    if card.user_id and card.user_id == user.id:
        return True
    return bool(card.student and card.student.parent_id == user.id)


def can_view_card(user: User, card: Card) -> bool:
    return is_staff(user) or owns_card(user, card)


def can_recharge_card(user: User, card: Card) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if user.role in {UserRole.EMPLEADO, UserRole.PADRE}:
        return owns_card(user, card)
    return False

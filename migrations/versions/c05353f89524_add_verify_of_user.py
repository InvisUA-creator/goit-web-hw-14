"""Add verify of user

Revision ID: c05353f89524
Revises: 88080dbcd2af
Create Date: 2024-12-10 22:14:22.722796

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c05353f89524"
down_revision: Union[str, None] = "88080dbcd2af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("confirmed", sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "confirmed")
    # ### end Alembic commands ###

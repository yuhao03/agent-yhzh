"""Add knowledge categories, model API protocol, and identity tables.

Revision ID: 0003_categories_protocol_accounts
Revises: 0002_model_provider_configs
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_categories_protocol_accounts"
down_revision = "0002_model_provider_configs"
branch_labels = None
depends_on = None


def _knowledge_schema(bind) -> str | None:
    return "knowledge" if bind.dialect.name == "postgresql" else None


def _identity_schema(bind) -> str | None:
    return "identity" if bind.dialect.name == "postgresql" else None


def upgrade() -> None:
    bind = op.get_bind()
    knowledge_schema = _knowledge_schema(bind)
    identity_schema = _identity_schema(bind)
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        op.execute("CREATE SCHEMA IF NOT EXISTS identity")

    knowledge_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_items", schema=knowledge_schema)
    }
    if "category" not in knowledge_columns:
        op.add_column(
            "knowledge_items",
            sa.Column(
                "category",
                sa.String(length=80),
                nullable=False,
                server_default="general",
            ),
            schema=knowledge_schema,
        )
        op.create_index(
            "ix_knowledge_items_category",
            "knowledge_items",
            ["category"],
            schema=knowledge_schema,
        )

    candidate_columns = {
        column["name"]
        for column in inspector.get_columns(
            "knowledge_candidates", schema=knowledge_schema
        )
    }
    if "category" not in candidate_columns:
        op.add_column(
            "knowledge_candidates",
            sa.Column(
                "category",
                sa.String(length=80),
                nullable=False,
                server_default="general",
            ),
            schema=knowledge_schema,
        )
        op.create_index(
            "ix_knowledge_candidates_category",
            "knowledge_candidates",
            ["category"],
            schema=knowledge_schema,
        )

    model_config_columns = {
        column["name"]
        for column in inspector.get_columns(
            "model_provider_configs", schema=knowledge_schema
        )
    }
    if "api_protocol" not in model_config_columns:
        op.add_column(
            "model_provider_configs",
            sa.Column(
                "api_protocol",
                sa.String(length=40),
                nullable=False,
                server_default="chat_completions_v1",
            ),
            schema=knowledge_schema,
        )

    if "user_accounts" not in inspector.get_table_names(schema=identity_schema):
        op.create_table(
            "user_accounts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.String(length=80), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("display_name", sa.String(length=160), nullable=False),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("role", sa.String(length=24), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("product_scope", sa.String(length=80), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "email", name="uq_user_account_email"),
            schema=identity_schema,
        )
        op.create_index(
            "ix_user_accounts_tenant_id",
            "user_accounts",
            ["tenant_id"],
            schema=identity_schema,
        )
        op.create_index(
            "ix_user_accounts_email",
            "user_accounts",
            ["email"],
            schema=identity_schema,
        )
        op.create_index(
            "ix_user_accounts_status",
            "user_accounts",
            ["status"],
            schema=identity_schema,
        )

    if "auth_sessions" not in inspector.get_table_names(schema=identity_schema):
        user_accounts_ref = (
            "identity.user_accounts.id"
            if bind.dialect.name == "postgresql"
            else "user_accounts.id"
        )
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("user_agent", sa.String(length=320), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_auth_session_token"),
            sa.ForeignKeyConstraint(
                ["user_id"], [user_accounts_ref], ondelete="CASCADE"
            ),
            schema=identity_schema,
        )
        op.create_index(
            "ix_auth_sessions_user_id",
            "auth_sessions",
            ["user_id"],
            schema=identity_schema,
        )
        op.create_index(
            "ix_auth_sessions_expires_at",
            "auth_sessions",
            ["expires_at"],
            schema=identity_schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    knowledge_schema = _knowledge_schema(bind)
    identity_schema = _identity_schema(bind)
    op.drop_table("auth_sessions", schema=identity_schema)
    op.drop_table("user_accounts", schema=identity_schema)
    op.drop_column("model_provider_configs", "api_protocol", schema=knowledge_schema)
    op.drop_index(
        "ix_knowledge_candidates_category",
        table_name="knowledge_candidates",
        schema=knowledge_schema,
    )
    op.drop_column("knowledge_candidates", "category", schema=knowledge_schema)
    op.drop_index(
        "ix_knowledge_items_category",
        table_name="knowledge_items",
        schema=knowledge_schema,
    )
    op.drop_column("knowledge_items", "category", schema=knowledge_schema)

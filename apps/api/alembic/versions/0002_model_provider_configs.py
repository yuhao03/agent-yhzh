"""Add encrypted model provider configuration.

Revision ID: 0002_model_provider_configs
Revises: 0001_platform_baseline
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_model_provider_configs"
down_revision = "0001_platform_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = "knowledge" if bind.dialect.name == "postgresql" else None
    inspector = sa.inspect(bind)
    if "model_provider_configs" in inspector.get_table_names(schema=schema):
        return
    op.create_table(
        "model_provider_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False),
        sa.Column("space_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("base_url", sa.String(length=1000), nullable=True),
        sa.Column("chat_model", sa.String(length=240), nullable=False),
        sa.Column("embedding_model", sa.String(length=240), nullable=True),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=True),
        sa.Column("api_key_hint", sa.String(length=32), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_message", sa.String(length=500), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "space_id", "name", name="uq_model_provider_config_name"
        ),
        schema=schema,
    )
    op.create_index(
        "ix_model_provider_configs_tenant_id",
        "model_provider_configs",
        ["tenant_id"],
        schema=schema,
    )
    op.create_index(
        "ix_model_provider_configs_space_id",
        "model_provider_configs",
        ["space_id"],
        schema=schema,
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = "knowledge" if bind.dialect.name == "postgresql" else None
    op.drop_table("model_provider_configs", schema=schema)

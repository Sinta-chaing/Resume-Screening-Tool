# Generated manually: resize ResumeChunk.embedding from 768 -> 1024 dims
# to match mxbai-embed-large (nomic-embed-text was removed).

import pgvector.django.vector
from django.db import migrations, models


def _forward_sql() -> str:
    # Zero-pad existing 768-dim vectors to 1024 dims (array_cat keeps old dims first).
    return (
        "ALTER TABLE screening_resumechunk "
        "ALTER COLUMN embedding TYPE vector(1024) USING "
        "array_cat(embedding::float4[], array_fill(0.0::float4, ARRAY[256]))::vector(1024);"
    )


def _reverse_sql() -> str:
    # Truncate back to 768 dims (rollback path).
    return (
        "ALTER TABLE screening_resumechunk "
        "ALTER COLUMN embedding TYPE vector(768) USING "
        "((embedding::float4[])[1:768])::float4[]::vector(768);"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("screening", "0002_analysissession_candidate_name_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=_forward_sql(), reverse_sql=_reverse_sql()),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="resumechunk",
                    name="embedding",
                    field=pgvector.django.vector.VectorField(dimensions=1024),
                ),
            ],
        ),
    ]
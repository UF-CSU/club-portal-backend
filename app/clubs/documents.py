"""
Club documents.
"""

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Club, ClubTag


@registry.register_document
class ClubDocument(Document):
    """
    Elasticsearch document for Club model
    """

    id = fields.IntegerField(attr="id")
    name = fields.TextField(
        attr='name',
        fields={
            'raw': fields.KeywordField(),
        },
    )
    instagram_followers = fields.IntegerField()
    founding_year = fields.IntegerField()
    tags = fields.NestedField(
        properties={
            'id': fields.IntegerField()
        }
    )

    class Index:
        name = 'clubs'

    class Django:
        model = Club
        related_models = [ClubTag]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, ClubTag):
            return related_instance.clubs.all()
        return []
from django.conf import settings
from django.core import urlresolvers
from django.core.cache import cache
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey


class Translation(models.Model):
    """
    Model that stores all translations
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    lang = models.CharField(max_length=5, db_index=True)
    field = models.CharField(max_length=255, db_index=True)
    translation = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['lang', 'field']
        unique_together = (('content_type', 'object_id', 'lang', 'field'),)

    def __unicode__(self):
        return u'%s : %s : %s' % (self.content_object, self.lang, self.field)


class Translatable(object):
    """
    Make your model extend this class to enable this API in you model instance
    instances.
    """
    translatable_fields = ()

    def translate(self):
        """
        Create all translations objects for this Translatable instance.

        @rtype: list of Translation objects
        @return: Returns a list of translations objects
        """
        translations = []
        for lang in settings.LANGUAGES:
            for field in self.translatable_fields:
                trans, created = Translation.objects.get_or_create(
                    object_id=self.id,
                    content_type=ContentType.objects.get_for_model(self),
                    field=field,
                    lang=lang[0],
                )
                translations.append(trans)
        return translations

    def translations(self, lang):
        """
        Return the complete list of translation objects of a Translatable
        instance

        @type lang: string
        @param lang: a string with the name of the language

        @rtype: list of Translation
        @return: Returns a list of translations objects
        """
        return Translation.objects.filter(
            object_id=self.id,
            content_type=ContentType.objects.get_for_model(self),
            lang=lang
        )

    def get_translation_obj(self, lang, field):
        """
        Return the translation object of an specific field in a Translatable
        istance

        @type lang: string
        @param lang: a string with the name of the language

        @type field: string
        @param field: a string with the name that we try to get

        @rtype: Translation
        @return: Returns a translation object
        """
        trans, created = Translation.objects.get_or_create(
                object_id=self.id,
                content_type=ContentType.objects.get_for_model(self),
                lang=lang,
                field=field,
            )
        return trans

    def _get_translation_cache_key(self, lang, field):
        content_type = self._meta.object_name
        return '%s:%s:%s:%s' % (content_type, self.id, lang, field)

    def get_translation(self, lang, field):
        """
        Return the translation string of an specific field in a Translatable
        istance

        @type lang: string
        @param lang: a string with the name of the language

        @type field: string
        @param field: a string with the name that we try to get

        @rtype: string
        @return: Returns a translation string
        """
        # Read from cache
        key = self._get_translation_cache_key(lang, field)
        trans = cache.get(key, '')
        if not trans:
            trans_obj = self.get_translation_obj(lang, field)
            trans =  getattr(trans_obj, 'translation', '')
            # if there's no translation text fall back to the model field
            if not trans:
                trans = getattr(self, field, '')
            # update cache
            cache.set(key, trans)
        return trans


    def set_translation(self, lang, field, text):
        """
        Store a translation string in the specified field for a Translatable
        istance

        @type lang: string
        @param lang: a string with the name of the language

        @type field: string
        @param field: a string with the name that we try to get

        @type text: string
        @param text: a string to be stored as translation of the field
        """
        trans_obj = self.get_translation_obj(lang, field)
        trans_obj.translation = text
        trans_obj.save()
        # Update cache
        key = self._get_translation_cache_key(lang, field)
        cache.set(key, text)
        return trans_obj

    def translations_link(self):
        """
        Print on admin change list the link to see all translations for this object

        @type text: string
        @param text: a string with the html to link to the translations admin interface
        """
        translation_type = ContentType.objects.get_for_model(Translation)
        link = urlresolvers.reverse('admin:%s_%s_changelist' % (
            translation_type.app_label,
            translation_type.model),
        )
        object_type = ContentType.objects.get_for_model(self)
        link += '?content_type__id__exact=%s&object_id=%s' % (object_type.id, self.id)
        return '<a href="%s">translate</a>' % link
    translations_link.allow_tags = True
    translations_link.short_description = 'Translations'

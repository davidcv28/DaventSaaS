from rest_framework import serializers

from StoreApp.domains.feed.models import FeedPost
from StoreApp.domains.feed.services import (
    POLL_OPTIONS_MAX,
    POLL_OPTIONS_MIN,
    apply_poll_options,
    detect_embed_provider,
)

"""

Serializers de escritura del dominio Feed (la serialización pública/
owner vive en services.feed — payload plano como legalpages).

"""

#=========================================
# POST WRITE (dueño — su tienda en context['store'])
#=========================================
class FeedPostWriteSerializer(serializers.Serializer):
    kind            =   serializers.ChoiceField(choices = FeedPost.KIND_CHOICES)
    caption         =   serializers.CharField(max_length = 2200, required = False, allow_blank = True, default = '')
    embed_url       =   serializers.URLField(max_length = 500, required = False, allow_blank = True, default = '')
    options         =   serializers.ListField(
        child           =   serializers.CharField(max_length = 90, allow_blank = False),
        required        =   False,
    )
    is_published    =   serializers.BooleanField(required = False, default = True)
    def validate_options(self, labels):
        cleaned     =   [str(label).strip() for label in labels if str(label).strip()]
        unique      =   list(dict.fromkeys(cleaned))
        if not (POLL_OPTIONS_MIN <= len(unique) <= POLL_OPTIONS_MAX):
            raise serializers.ValidationError(f'La encuesta necesita entre {POLL_OPTIONS_MIN} y {POLL_OPTIONS_MAX} opciones distintas.')
        return unique
    def validate(self, attrs):
        post        =   self.instance
        kind        =   attrs.get('kind', getattr(post, 'kind', None))
        caption     =   (attrs.get('caption') or '').strip()
        embed_url   =   (attrs.get('embed_url') or '').strip()
        #El tipo no se edita: una encuesta no se convierte en video (sus
        #votos/opciones quedarían huérfanos de significado).
        if post is not None and 'kind' in attrs and attrs['kind'] != post.kind:
            raise serializers.ValidationError({'kind': 'El tipo de publicación no se puede cambiar.'})
        if kind == FeedPost.KIND_TEXT and not caption:
            raise serializers.ValidationError({'caption': 'Escribí el texto de la publicación.'})
        if kind == FeedPost.KIND_POLL:
            if not caption:
                raise serializers.ValidationError({'caption': 'Escribí la pregunta de la encuesta.'})
            if post is None and 'options' not in attrs:
                raise serializers.ValidationError({'options': 'La encuesta necesita sus opciones.'})
        if kind == FeedPost.KIND_EMBED:
            if not embed_url:
                raise serializers.ValidationError({'embed_url': 'Pegá el link de la publicación.'})
            provider        =   detect_embed_provider(embed_url)
            if not provider:
                raise serializers.ValidationError({'embed_url': 'Link no admitido: usá una publicación de TikTok, YouTube, Instagram, Facebook o X.'})
            attrs['embed_provider']     =   provider
            attrs['embed_url']          =   embed_url
        else:
            #Un post no-embed no puede conservar URL de red vieja.
            attrs['embed_url']          =   ''
            attrs['embed_provider']     =   ''
        attrs['caption']    =   caption
        return attrs
    def create(self, validated_data):
        options     =   validated_data.pop('options', None)
        post        =   FeedPost.objects.create(**validated_data)
        if post.kind == FeedPost.KIND_POLL and options:
            apply_poll_options(post, options)
        return post
    def update(self, post, validated_data):
        options     =   validated_data.pop('options', None)
        for field, value in validated_data.items():
            setattr(post, field, value)
        post.save()
        if post.kind == FeedPost.KIND_POLL and options is not None:
            apply_poll_options(post, options)
        return post
#=========================================
# COMMENT WRITE (comprador autenticado)
#=========================================
class FeedCommentWriteSerializer(serializers.Serializer):
    body            =   serializers.CharField(max_length = 600, trim_whitespace = True)
    def validate_body(self, body):
        if not body:
            raise serializers.ValidationError('Escribí tu comentario.')
        return body
#=========================================
# VOTE WRITE (comprador autenticado)
#=========================================
class FeedVoteSerializer(serializers.Serializer):
    option          =   serializers.IntegerField(min_value = 1)
#=========================================
# MODERATION WRITE (dueño — ocultar/mostrar comentario)
#=========================================
class FeedCommentModerationSerializer(serializers.Serializer):
    is_hidden       =   serializers.BooleanField()

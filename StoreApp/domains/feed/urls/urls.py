from django.urls import path, re_path

from StoreApp.domains.feed.views import (
    PublicFeedCommentsView,
    PublicFeedLikeView,
    PublicFeedMyCommentView,
    PublicFeedView,
    PublicFeedVoteView,
    StoreFeedCommentDetailView,
    StoreFeedCommentsView,
    StoreFeedPostDetailView,
    StoreFeedPostMediaView,
    StoreFeedPostsView,
)

"""
URLs del dominio feed (incluidas bajo /api/ por DaventProject/urls).

Dueño: store-feed/* — tienda del usuario logueado (IDOR 404, gate
has_feed → 403). Público: stores/public/<slug>/feed/* — misma regla de
visibilidad que el resto de la web pública + el flag del plan.
"""
urlpatterns = [
    #=========================================
    # DUEÑO (auth DAVENT — su tienda)
    #=========================================
    path('store-feed/posts/',                             StoreFeedPostsView.as_view(),         name = 'feed-posts'),
    path('store-feed/posts/<int:pk>/',                    StoreFeedPostDetailView.as_view(),    name = 'feed-post-detail'),
    path('store-feed/posts/<int:pk>/media/',              StoreFeedPostMediaView.as_view(),     name = 'feed-post-media'),
    path('store-feed/comments/',                          StoreFeedCommentsView.as_view(),      name = 'feed-comments'),
    path('store-feed/comments/<int:pk>/',                 StoreFeedCommentDetailView.as_view(), name = 'feed-comment-detail'),
    #=========================================
    # PÚBLICO (web de la tienda)
    #=========================================
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/feed/$',                        PublicFeedView.as_view(),         name = 'public-feed'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/feed/(?P<pk>[0-9]+)/comments/$', PublicFeedCommentsView.as_view(), name = 'public-feed-comments'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/feed/comments/(?P<pk>[0-9]+)/$', PublicFeedMyCommentView.as_view(), name = 'public-feed-my-comment'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/feed/(?P<pk>[0-9]+)/like/$',     PublicFeedLikeView.as_view(),     name = 'public-feed-like'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/feed/(?P<pk>[0-9]+)/vote/$',     PublicFeedVoteView.as_view(),     name = 'public-feed-vote'),
]

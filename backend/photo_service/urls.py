from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    path("query/", csrf_exempt(views.QueryView.as_view()),
         name="query"),

    path("caption/", csrf_exempt(views.ImageCaptionView.as_view()),
         name="caption"),

    path("face/", csrf_exempt(views.FaceDetectionView.as_view()),
         name="face"),

    path("upload/", csrf_exempt(views.ImageUploadView.as_view()),
         name="upload"),

    path("albumization/", csrf_exempt(views.AlbumizationView.as_view()),
         name="albumization"),

    # Photos
    path('photos/', csrf_exempt(views.ListPhotosView.as_view()), name='list_photos'),

    path('photos/<str:photo_id>/',
         csrf_exempt(views.PhotoDetailView.as_view()), name='photo_detail'),

    # Albums
    path('albums/', csrf_exempt(views.ListAlbumsView.as_view()), name='list_albums'),

    path('albums/<str:album_id>/',
         csrf_exempt(views.AlbumDetailView.as_view()), name='album_detail'),

    path('albums/<str:album_id>/photos/',
         csrf_exempt(views.AlbumPhotosView.as_view()), name='album_photos'),

    # Stats
    path('stats/', csrf_exempt(views.StatsView.as_view()), name='stats'),

]

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
         name="albumization")
]

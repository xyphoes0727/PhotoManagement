from django.db import models
# Create your models here.


class Face(models.Model):
    FaceId = models.BigIntegerField(primary_key=True, null=False, unique=True)
    OnPinecone = models.BooleanField(default=False)
    # str for lazy relationship
    Images = models.ManyToManyField("Image")


class Image(models.Model):
    # Same ID as Pinecone Ref.
    ImageId = models.BigIntegerField(primary_key=True, null=False, unique=True)

    ObjectName = models.CharField(null=True)
    Caption = models.CharField(null=True)
    Faces = models.ManyToManyField(Face)
    AlbumId = models.BigIntegerField(null=False, default=0)
    CreatedAt = models.DateTimeField(null=True)
    FaceCount = models.SmallIntegerField(default=0)
    OnPinecone = models.BooleanField(default=False)
    IsFaceRecognised = models.BooleanField(default=False)

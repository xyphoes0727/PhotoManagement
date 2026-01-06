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
    OnPinecone = models.BooleanField(default=False)
    IsFaceRecognised = models.BooleanField(default=False)
    Faces = models.ManyToManyField(Face)

# apps/core/models.py
from django.db import models
from django.utils import timezone

class Upload(models.Model):
    file = models.FileField(upload_to="uploads/")
    original_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "pending"), ("validating", "validating"), ("done", "done"), ("failed", "failed")],
        default="pending",
    )
    corrected_file = models.FileField(upload_to="corrected/", null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)

class ValidationIssue(models.Model):
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="issues")
    line_no = models.IntegerField()
    reg = models.CharField(max_length=10)
    rule_id = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=[("error","error"),("warn","warn")])
    message = models.TextField()
    fixed = models.BooleanField(default=False)
    suggestion = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
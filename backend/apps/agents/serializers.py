from __future__ import annotations

from rest_framework import serializers

from apps.agents.models import Agent, AgentCommand, AgentFolder


class AgentFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentFolder
        fields = [
            "id",
            "local_path",
            "label",
            "is_active",
            "last_scanned_at",
            "file_count",
        ]
        read_only_fields = ["id", "last_scanned_at", "file_count"]


class AgentCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCommand
        fields = [
            "id",
            "command_type",
            "payload",
            "status",
            "result",
            "created_at",
            "executed_at",
        ]
        read_only_fields = fields


class AgentSerializer(serializers.ModelSerializer):
    folders = AgentFolderSerializer(many=True, read_only=True)
    pending_commands_count = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "agent_id",
            "name",
            "status",
            "sync_interval_minutes",
            "max_file_size_mb",
            "push_original_files",
            "platform",
            "hostname",
            "ip_address",
            "agent_version",
            "capabilities",
            "last_seen",
            "last_sync_at",
            "files_count",
            "total_size_bytes",
            "folders",
            "pending_commands_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_seen",
            "last_sync_at",
            "files_count",
            "total_size_bytes",
            "created_at",
            "updated_at",
        ]

    def get_pending_commands_count(self, obj) -> int:
        return obj.commands.filter(status="pending").count()


class AgentCreateSerializer(serializers.ModelSerializer):
    """Serializer for registering a new agent."""

    folders = AgentFolderSerializer(many=True, required=False)

    class Meta:
        model = Agent
        fields = [
            "agent_id",
            "name",
            "platform",
            "hostname",
            "agent_version",
            "capabilities",
            "push_original_files",
            "folders",
        ]

    def validate_agent_id(self, value):
        if Agent.objects.filter(agent_id=value).exists():
            raise serializers.ValidationError("An agent with this ID already exists.")
        return value

    def create(self, validated_data):
        folders_data = validated_data.pop("folders", [])
        agent = Agent.objects.create(**validated_data)
        for folder_data in folders_data:
            AgentFolder.objects.create(agent=agent, **folder_data)
        return agent


class AgentHeartbeatSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Agent.Status.choices,
        default=Agent.Status.ONLINE,
    )
    platform = serializers.CharField(max_length=50, required=False, default="")
    hostname = serializers.CharField(max_length=255, required=False, default="")
    ip_address = serializers.IPAddressField(required=False, default=None)
    agent_version = serializers.CharField(max_length=20, required=False, default="")
    files_count = serializers.IntegerField(required=False, default=0)
    total_size_bytes = serializers.IntegerField(required=False, default=0)
    uptime_seconds = serializers.IntegerField(required=False, default=0)
    folders_monitored = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class SyncFileSerializer(serializers.Serializer):
    local_path = serializers.CharField(max_length=1024)
    file_hash = serializers.CharField(max_length=128)
    file_size = serializers.IntegerField()
    mime_type = serializers.CharField(max_length=255, required=False, default="")
    modified_at = serializers.CharField(required=False, default="")
    metadata = serializers.DictField(required=False, default=dict)
    extracted_text = serializers.CharField(required=False, default="")
    markdown = serializers.CharField(required=False, default="")
    classification = serializers.DictField(required=False, default=dict)
    entities = serializers.ListField(required=False, default=list)
    summary = serializers.CharField(required=False, default="", allow_blank=True)
    embeddings = serializers.ListField(
        child=serializers.FloatField(), required=False, default=list
    )
    processing_status = serializers.CharField(required=False, default="completed")
    chunk_count = serializers.IntegerField(required=False, default=0)
    ocr_used = serializers.BooleanField(required=False, default=False)


class AgentSyncSerializer(serializers.Serializer):
    files = SyncFileSerializer(many=True)
    stats = serializers.DictField(required=False, default=dict)
    original_files = serializers.DictField(
        required=False,
        default=dict,
        help_text="Mapping of local_path -> base64 file bytes (optional).",
    )

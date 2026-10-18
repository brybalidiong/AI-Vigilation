from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def subject_exam_group(subject_id):
    return f'subject_exams_{subject_id}'


def notify_exam_published(subject_id):
    """Tell connected students to reload their authorized exam list."""
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            subject_exam_group(subject_id),
            {'type': 'exam_published'},
        )

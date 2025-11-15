from django.core.management.base import BaseCommand
from main.views import check_pending_messages

class Command(BaseCommand):
    help = 'Send monitoring report for pending messages'
    
    def handle(self, *args, **options):
        check_pending_messages()
        self.stdout.write(
            self.style.SUCCESS('Monitoring report sent successfully')
        )

from django.core.management.base import BaseCommand
from judging.models import Criterion


class Command(BaseCommand):
    help = 'Seed fixed criteria with weights'

    def handle(self, *args, **options):
        criteria_data = [
            {'name': 'Innovation & Creativity', 'weight': 0.25},
            {'name': 'Market Potential', 'weight': 0.25},
            {'name': 'Feasibility', 'weight': 0.20},
            {'name': 'Team & Execution', 'weight': 0.15},
            {'name': 'Presentation Quality', 'weight': 0.15},
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in criteria_data:
            criterion, created = Criterion.objects.get_or_create(
                name=data['name'],
                defaults={'weight': data['weight']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created criterion: {criterion.name} (weight: {criterion.weight})')
                )
            else:
                # Update weight if it changed
                if criterion.weight != data['weight']:
                    criterion.weight = data['weight']
                    criterion.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated criterion: {criterion.name} (weight: {criterion.weight})')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully seeded criteria: {created_count} created, {updated_count} updated'
            )
        )

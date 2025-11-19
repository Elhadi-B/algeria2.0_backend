import csv
import os
from django.core.management.base import BaseCommand
from judging.models import Judge


class Command(BaseCommand):
    help = 'Generate judge tokens (bulk create judges or generate tokens for existing judges)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            help='Number of judges to create (with auto-generated data)'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to CSV file with judge data (name, email, organization, phone)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without creating'
        )

    def handle(self, *args, **options):
        count = options.get('count')
        file_path = options.get('file')
        dry_run = options.get('dry_run', False)
        
        if not count and not file_path:
            self.stdout.write(self.style.ERROR('Must provide either --count or --file'))
            return
        
        judges_data = []
        
        if file_path:
            # Read from CSV
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        judges_data.append({
                            'name': row.get('name', ''),
                            'email': row.get('email', ''),
                            'organization': row.get('organization', ''),
                            'phone': row.get('phone', ''),
                            'image_path': row.get('image_path', '')
                        })
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error reading file: {str(e)}'))
                return
        elif count:
            # Generate dummy data
            for i in range(1, count + 1):
                judges_data.append({
                    'name': f'Judge {i}',
                    'email': f'judge{i}@example.com',
                    'organization': f'Organization {i}',
                    'phone': '',
                    'image_path': ''
                })
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - Preview:'))
            for judge_data in judges_data:
                self.stdout.write(f"  - {judge_data['name']} ({judge_data['email']})")
            self.stdout.write(self.style.WARNING('\nWould create {} judges'.format(len(judges_data))))
            return
        
        # Create judges
        created_judges = []
        for judge_data in judges_data:
            if not judge_data.get('name') or not judge_data.get('email'):
                self.stdout.write(self.style.WARNING(f'Skipping invalid judge data: {judge_data}'))
                continue
            
            judge, created = Judge.objects.get_or_create(
                email=judge_data['email'],
                defaults={
                    'name': judge_data['name'],
                    'organization': judge_data.get('organization', ''),
                    'phone': judge_data.get('phone', ''),
                    'image_path': judge_data.get('image_path', '')
                }
            )
            
            if not created:
                # Update existing judge
                judge.name = judge_data['name']
                judge.organization = judge_data.get('organization', '')
                judge.phone = judge_data.get('phone', '')
                judge.image_path = judge_data.get('image_path', '')
                judge.save()
            
            created_judges.append(judge)
        
        # Export tokens to CSV
        output_file = 'judge_tokens.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['judge_id', 'name', 'email', 'token', 'link'])
            
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            
            for judge in created_judges:
                login_url = f"{base_url}/api/judge/login/?token={judge.token}"
                writer.writerow([
                    judge.id,
                    judge.name,
                    judge.email,
                    str(judge.token),
                    login_url
                ])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully processed {len(created_judges)} judges'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f'Tokens exported to: {output_file}')
        )

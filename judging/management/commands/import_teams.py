import csv
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from judging.models import Team


class Command(BaseCommand):
    help = 'Import teams from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without committing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                preview_rows = []
                errors = []
                rows_to_import = []
                
                for idx, row in enumerate(reader, start=2):
                    row_errors = []
                    
                    # Validate required fields
                    if not row.get('project_name'):
                        row_errors.append(f"Row {idx}: Missing project_name")
                    
                    if not row.get('short_description'):
                        row_errors.append(f"Row {idx}: Missing short_description")
                    
                    if row_errors:
                        errors.extend(row_errors)
                        continue
                    
                    # Parse extra_info if present
                    extra_info = {}
                    if row.get('extra_info'):
                        try:
                            extra_info = json.loads(row['extra_info'])
                        except:
                            extra_info = {'raw': row['extra_info']}
                    
                    team_data = {
                        'project_name': row['project_name'],
                        'short_description': row['short_description'],
                        'members': row.get('members', ''),
                        'image_path': row.get('image_path', ''),
                        'extra_info': extra_info
                    }
                    
                    preview_rows.append(team_data)
                    rows_to_import.append(team_data)
                
                # Display preview
                self.stdout.write(f'\nPreview ({len(preview_rows)} rows):')
                self.stdout.write('=' * 80)
                for i, row in enumerate(preview_rows[:10], 1):
                    self.stdout.write(f"{i}. {row['project_name']}: {row['short_description'][:50]}...")
                
                if len(preview_rows) > 10:
                    self.stdout.write(f'... and {len(preview_rows) - 10} more rows')
                
                if errors:
                    self.stdout.write(self.style.ERROR(f'\nErrors ({len(errors)}):'))
                    for error in errors:
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\nDRY RUN: No data was imported'))
                    return
                
                # Import if not dry run
                if not errors:
                    with transaction.atomic():
                        created = []
                        for team_data in rows_to_import:
                            team = Team.objects.create(**team_data)
                            created.append(team)
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'\nSuccessfully imported {len(created)} teams')
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR('\nImport aborted due to errors. Fix errors and try again.')
                    )
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))

import csv
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

                    num_equipe = (row.get('num_equipe') or row.get('id') or '').strip()
                    nom_equipe = (row.get('nom_equipe') or row.get('name') or '').strip()

                    if not num_equipe:
                        row_errors.append(f"Row {idx}: Missing num_equipe")
                    if not nom_equipe:
                        row_errors.append(f"Row {idx}: Missing nom_equipe")

                    if row_errors:
                        errors.extend(row_errors)
                        continue

                    team_data = {
                        'num_equipe': num_equipe,
                        'nom_equipe': nom_equipe,
                    }

                    preview_rows.append(team_data)
                    rows_to_import.append(team_data)
                
                # Display preview
                self.stdout.write(f'\nPreview ({len(preview_rows)} rows):')
                self.stdout.write('=' * 80)
                for i, row in enumerate(preview_rows[:10], 1):
                    self.stdout.write(f"{i}. #{row['num_equipe']} - {row['nom_equipe']}")
                
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
                            team, created_flag = Team.objects.update_or_create(
                                num_equipe=team_data['num_equipe'],
                                defaults={'nom_equipe': team_data['nom_equipe']}
                            )
                            if created_flag:
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

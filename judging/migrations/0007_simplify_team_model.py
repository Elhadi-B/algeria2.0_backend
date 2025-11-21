from django.db import migrations, models


def populate_num_equipe(apps, schema_editor):
    Team = apps.get_model('judging', 'Team')
    for team in Team.objects.all().order_by('pk'):
        team.num_equipe = str(team.id)
        team.save(update_fields=['num_equipe'])


class Migration(migrations.Migration):

    dependencies = [
        ('judging', '0006_alter_criterion_key_alter_criterion_order_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='team',
            old_name='project_name',
            new_name='nom_equipe',
        ),
        migrations.RemoveConstraint(
            model_name='team',
            name='unique_project_name',
        ),
        migrations.AddField(
            model_name='team',
            name='num_equipe',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.RunPython(populate_num_equipe, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='team',
            name='num_equipe',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='evaluation',
            name='team',
            field=models.ForeignKey(on_delete=models.CASCADE, related_name='evaluations', to='judging.team', to_field='num_equipe'),
        ),
        migrations.RemoveField(
            model_name='team',
            name='team_leader_name',
        ),
        migrations.RemoveField(
            model_name='team',
            name='team_leader_year',
        ),
        migrations.RemoveField(
            model_name='team',
            name='team_leader_email',
        ),
        migrations.RemoveField(
            model_name='team',
            name='team_leader_phone',
        ),
        migrations.RemoveField(
            model_name='team',
            name='project_domain',
        ),
        migrations.RemoveField(
            model_name='team',
            name='short_description',
        ),
        migrations.RemoveField(
            model_name='team',
            name='members',
        ),
        migrations.RemoveField(
            model_name='team',
            name='extra_info',
        ),
        migrations.RemoveField(
            model_name='team',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='team',
            name='updated_at',
        ),
        migrations.AlterModelOptions(
            name='team',
            options={'ordering': ['nom_equipe']},
        ),
        migrations.RemoveField(
            model_name='team',
            name='id',
        ),
        migrations.AlterField(
            model_name='team',
            name='num_equipe',
            field=models.CharField(max_length=50, primary_key=True, serialize=False),
        ),
    ]


"""
Script to create admin user with default password
Run: python manage.py shell < create_admin.py
Or: python -c "exec(open('create_admin.py').read())"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitching_day.settings')
django.setup()

from django.contrib.auth.models import User

username = 'admin'
email = 'admin@example.com'
password = 'admin123'  # Change this password!

if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f'Updated admin user "{username}" with new password')
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Created admin user "{username}" with password: {password}')
    print('\n⚠️ IMPORTANT: Change the default password after first login!')

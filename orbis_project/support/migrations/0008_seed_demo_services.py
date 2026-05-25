from django.db import migrations


def create_demo_services(apps, schema_editor):
    Service = apps.get_model('support', 'Service')
    demo = [
        {
            'name': 'IT Support',
            'description': '24/7 IT support for your organization.',
            'plan': 'pro',
            'features': 'Email support,Phone support,On-site visits',
            'price': '49.99',
        },
        {
            'name': 'Customer Support Desk',
            'description': 'Full customer support desk solution.',
            'plan': 'enterprise',
            'features': 'Multichannel support,SLAs,Reporting',
            'price': '199.00',
        },
        {
            'name': 'Software Maintenance',
            'description': 'Ongoing maintenance for software products.',
            'plan': 'basic',
            'features': 'Bug fixes,Minor updates',
            'price': '19.99',
        },
        {
            'name': 'Website Management',
            'description': 'Professional website management and updates.',
            'plan': 'pro',
            'features': 'Content updates,Performance monitoring,SSL management',
            'price': '79.99',
        },
        {
            'name': 'Cloud & Hosting Support',
            'description': 'Expert support for cloud and hosting infrastructure.',
            'plan': 'enterprise',
            'features': 'Infrastructure monitoring,Auto-scaling setup,24/7 support',
            'price': '149.99',
        },
        {
            'name': 'Technical Consultation',
            'description': 'Expert technical advice and planning services.',
            'plan': 'pro',
            'features': 'Architecture review,Performance optimization,Security audit',
            'price': '99.99',
        },
        {
            'name': 'Cloud Storage',
            'description': 'Secure cloud storage with collaboration features.',
            'plan': 'enterprise',
            'features': '500GB storage,Version control,File sharing,Encryption',
            'price': '29.99',
        },
    ]

    for s in demo:
        Service.objects.get_or_create(name=s['name'], defaults={
            'description': s['description'],
            'plan': s['plan'],
            'features': s['features'],
            'price': s['price'],
        })


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0007_remove_profile_image_profile_profile_photo'),
    ]

    operations = [
        migrations.RunPython(create_demo_services),
    ]

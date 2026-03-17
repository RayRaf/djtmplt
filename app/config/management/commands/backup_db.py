from django.core.management.base import BaseCommand, CommandError

from config.backups import (
    build_backup_filename,
    build_backup_object_key,
    cleanup_temp_dir,
    create_temp_backup_dir,
    dump_database,
    get_database_cli_config,
    get_s3_backup_config,
    upload_backup,
)


class Command(BaseCommand):
    help = "Create a PostgreSQL backup and upload it to S3-compatible storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--filename",
            default=None,
            help="Custom dump filename. Default: <db>_<timestamp>.dump",
        )
        parser.add_argument(
            "--prefix",
            default=None,
            help="Override DB_BACKUP_S3_PREFIX for this command.",
        )
        parser.add_argument(
            "--keep-local",
            action="store_true",
            help="Keep the generated dump file on disk after upload.",
        )

    def handle(self, *args, **options):
        temp_dir = create_temp_backup_dir()

        try:
            db = get_database_cli_config()
            s3_config = get_s3_backup_config(options["prefix"])
            filename = options["filename"] or build_backup_filename(db.name)
            local_path = temp_dir / filename
            object_key = build_backup_object_key(s3_config.prefix, filename)

            self.stdout.write(f"Creating dump '{filename}'...")
            dump_database(local_path)

            self.stdout.write(
                f"Uploading to s3://{s3_config.bucket}/{object_key}..."
            )
            upload_backup(local_path, object_key, s3_config)

            if options["keep_local"]:
                self.stdout.write(
                    self.style.WARNING(f"Local dump kept at {local_path}")
                )
                self.stdout.write(self.style.SUCCESS(object_key))
                return

            cleanup_temp_dir(temp_dir)
            self.stdout.write(self.style.SUCCESS(object_key))
        except Exception as exc:
            cleanup_temp_dir(temp_dir)
            raise CommandError(str(exc)) from exc
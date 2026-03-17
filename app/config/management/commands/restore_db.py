from django.core.management.base import BaseCommand, CommandError

from config.backups import (
    cleanup_temp_dir,
    create_temp_backup_dir,
    download_backup,
    find_latest_backup_key,
    get_s3_backup_config,
    restore_database,
)


class Command(BaseCommand):
    help = "Restore the PostgreSQL database from an S3 backup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            default=None,
            help="Full S3 object key to restore from.",
        )
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Restore the newest backup under the configured project prefix.",
        )
        parser.add_argument(
            "--prefix",
            default=None,
            help="Override DB_BACKUP_S3_PREFIX for latest-backup lookup.",
        )
        parser.add_argument(
            "--keep-local",
            action="store_true",
            help="Keep the downloaded dump file on disk after restore.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Required confirmation flag because restore overwrites database contents.",
        )

    def handle(self, *args, **options):
        if bool(options["key"]) == bool(options["latest"]):
            raise CommandError("Specify exactly one of --key or --latest.")

        if not options["yes"]:
            raise CommandError("Pass --yes to confirm destructive restore.")

        temp_dir = create_temp_backup_dir()

        try:
            s3_config = get_s3_backup_config(options["prefix"])
            object_key = options["key"] or find_latest_backup_key(s3_config)
            filename = object_key.rsplit("/", 1)[-1]
            local_path = temp_dir / filename

            self.stdout.write(
                f"Downloading s3://{s3_config.bucket}/{object_key}..."
            )
            download_backup(object_key, local_path, s3_config)

            self.stdout.write("Restoring database...")
            restore_database(local_path)

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
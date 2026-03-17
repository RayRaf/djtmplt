import json

from django.core.management.base import BaseCommand

from config.health import build_readiness_report


class Command(BaseCommand):
    help = "Run readiness checks for database, cache, broker, and runtime process."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-migrations",
            action="store_true",
            help="Skip unapplied migration checks.",
        )
        parser.add_argument(
            "--check-broker",
            action="store_true",
            help="Check Celery broker connectivity.",
        )
        parser.add_argument(
            "--expect-process",
            default=None,
            help="Require PID 1 command line to contain this substring.",
        )

    def handle(self, *args, **options):
        report = build_readiness_report(
            check_migrations=not options["skip_migrations"],
            check_broker=options["check_broker"],
            expected_process=options["expect_process"],
        )
        output = json.dumps(report, sort_keys=True)

        if report["status"] == "ok":
            self.stdout.write(output)
            return

        self.stderr.write(output)
        raise SystemExit(1)
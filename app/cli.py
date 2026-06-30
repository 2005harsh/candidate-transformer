import click
import json
import sys
from pathlib import Path
from typing import List, Optional
from app.parsers.factory import ParserFactory
from app.services.normalizer import Normalizer
from app.services.merge_engine import MergeEngine
from app.services.projection import ProjectionEngine
from app.validators.output_validator import OutputValidator


@click.command()
@click.option('--inputs', '-i', multiple=True, required=True, help='Input source files or URLs')
@click.option('--config', '-c', help='Runtime configuration JSON file')
@click.option('--output', '-o', default='output.json', help='Output JSON file path')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def main(inputs: List[str], config: Optional[str], output: str, debug: bool):
    """Multi-Source Candidate Data Transformer CLI."""
    
    click.echo("=" * 60)
    click.echo("CANDIDATE DATA TRANSFORMER PIPELINE")
    click.echo("=" * 60)
    
    try:
        # Parse sources
        sources = []
        click.echo(f"\n📁 Processing {len(inputs)} source(s)...")
        
        for input_path in inputs:
            click.echo(f"  • {input_path}")
            try:
                parser = ParserFactory.create_parser(input_path)
            except Exception as e:
                click.echo(f"    ❌ Could not create parser: {e}")
                continue

            if not (parser and parser.validate_source()):
                click.echo(f"    ❌ Invalid or unsupported source")
                continue

            try:
                data = parser.parse()
            except Exception as e:
                # A garbage/malformed single source must not crash the whole run.
                click.echo(f"    ❌ Failed to parse ({e}) — skipping source")
                continue

            if not data:
                click.echo(f"    ⚠️  No data extracted")
                continue

            # Some sources (e.g. CSV) can yield multiple candidate records.
            records = data if isinstance(data, list) else [data]

            added = 0
            for record_data in records:
                if not record_data or not isinstance(record_data, dict):
                    continue
                record_data = dict(record_data)
                record_data['_source'] = parser.get_source_name()
                record_data['_method'] = 'parse'
                sources.append(record_data)
                added += 1

            if added:
                click.echo(f"    ✅ Parsed: {added} record(s)")
            else:
                click.echo(f"    ⚠️  No usable records extracted")
        
        if not sources:
            click.echo("\n❌ Error: No valid sources found")
            click.echo("   Supported: JSON, PDF, CSV, TXT, DOCX, GitHub URLs")
            return 1
        
        click.echo(f"\n✅ Parsed {len(sources)} source(s)")
        
        # Normalize
        click.echo("\n🔄 Normalizing fields...")
        normalizer = Normalizer()
        normalized_sources = []
        for source in sources:
            normalized = normalizer.normalize_record(source)
            if normalized:
                normalized_sources.append(normalized)
        
        click.echo(f"   ✅ Normalized {len(normalized_sources)} source(s)")
        
        # Merge
        click.echo("\n🔗 Merging records...")
        merge_engine = MergeEngine()
        merge_result = merge_engine.merge(normalized_sources)

        # merge() returns a single CanonicalRecord when all sources cluster into
        # one candidate, or a List[CanonicalRecord] when multiple distinct
        # candidates were detected (e.g. a CSV with several rows). Normalize to
        # a list so the rest of the pipeline only has one code path.
        records = merge_result if isinstance(merge_result, list) else [merge_result]

        click.echo(f"   ✅ Merged into {len(records)} candidate record(s)")

        # Load config once (shared across all candidates)
        projection_config = {}
        if config:
            try:
                with open(config, 'r', encoding='utf-8') as f:
                    projection_config = json.load(f)
                click.echo(f"\n📋 Loaded config: {config}")
            except Exception as e:
                click.echo(f"\n⚠️  Could not load config: {e}")
                click.echo("   Using default projection")

        projection_engine = ProjectionEngine(projection_config)
        validator = OutputValidator(
            schema=projection_engine.get_output_schema(),
            required=projection_engine.get_required_fields(),
        )

        projected_outputs = []
        for idx, record in enumerate(records, start=1):
            click.echo(f"\n📊 Candidate {idx}/{len(records)} Summary:")
            click.echo(f"   Name: {record.full_name or 'Unnamed'}")
            click.echo(f"   Emails: {len(record.emails)}")
            click.echo(f"   Phones: {len(record.phones)}")
            click.echo(f"   Skills: {len(record.skills)}")
            click.echo(f"   Experience: {len(record.experience)}")
            click.echo(f"   Education: {len(record.education)}")
            click.echo(f"   Confidence: {record.overall_confidence:.2f}")
            click.echo(f"   Provenance: {len(record.provenance)} entries")

            if debug:
                click.echo("   🔍 Debug Info:")
                click.echo(f"      Candidate ID: {record.candidate_id}")
                if record.provenance:
                    click.echo("      Provenance:")
                    for p in record.provenance[:5]:
                        click.echo(f"        - {p.field}: {p.source} ({p.method})")

            try:
                projected = projection_engine.project(record)
            except Exception as e:
                click.echo(f"   ❌ Projection failed for candidate {idx}: {e}")
                continue

            if validator.validate(projected):
                click.echo(f"   ✅ Output validated against schema")
            else:
                click.echo(f"   ⚠️  Schema validation warnings:")
                for err in validator.get_errors():
                    click.echo(f"      - {err}")

            projected_outputs.append(projected)

        # Write output: a single object if there's exactly one candidate
        # (matches the schema in the assignment), otherwise a JSON array.
        output_data = projected_outputs[0] if len(projected_outputs) == 1 else projected_outputs

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)

        click.echo(f"\n   ✅ Output written to: {output}")

        # Show sample output (preview the first candidate's output)
        preview_source = projected_outputs[0] if projected_outputs else {}
        click.echo("\n📄 Output Preview:")
        preview = {k: v for k, v in list(preview_source.items())[:5]}
        for key, value in preview.items():
            if isinstance(value, list):
                click.echo(f"   {key}: [{len(value)} items]")
            else:
                click.echo(f"   {key}: {value}")
        if len(preview_source) > 5:
            click.echo(f"   ... and {len(preview_source) - 5} more fields")
        if len(projected_outputs) > 1:
            click.echo(f"   (showing 1 of {len(projected_outputs)} candidates in output array)")
        
        click.echo("\n" + "=" * 60)
        click.echo("✨ PIPELINE COMPLETE!")
        click.echo("=" * 60)
        
        return 0
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        else:
            click.echo("   Run with --debug for full traceback")
        return 1


if __name__ == '__main__':
    main()
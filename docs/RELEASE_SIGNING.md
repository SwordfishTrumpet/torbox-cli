# Release Signing Guide

This document describes how to sign and verify release artifacts for `torbox-cli`.

## Signing PyPI wheels and sdists with Sigstore

After building the distribution artifacts:

```bash
python -m build
python -m sigstore sign dist/*
```

This produces `.sigstore` bundles next to each artifact. Upload these bundles alongside the wheels/sdists when publishing to PyPI or attaching to a GitHub release.

## Verifying signatures

Consumers can verify the artifacts using:

```bash
python -m sigstore verify dist/torbox_cli-*.whl
```

Or for an attached bundle:

```bash
python -m sigstore verify --bundle torbox_cli-1.0.0-py3-none-any.whl.sigstore dist/torbox_cli-1.0.0-py3-none-any.whl
```

## SLSA provenance via GitHub Actions

To generate SLSA Level 3 provenance, use the official SLSA GitHub generator in your release workflow:

```yaml
- uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.9.0
  with:
    base64-subjects: "${{ steps.hash.outputs.hashes }}"
    upload-assets: true
```

Ensure the workflow hashes all release artifacts and passes them to the generator. The resulting provenance file should be attached to the GitHub release alongside the signed artifacts.

# Local Data Provenance

## MIND-small development split

- Original dataset: Microsoft News Dataset (MIND), ACL 2020.
- Official project: <https://msnews.github.io/>
- Official description and schema: <https://learn.microsoft.com/azure/open-datasets/dataset-microsoft-news>
- The original Azure blob returned HTTP 409 on 2026-08-07.
- Public mirror used: `gamusa/MIND` on Hugging Face.
- Download URL: `https://huggingface.co/datasets/gamusa/MIND/resolve/main/MINDsmall_dev.zip?download=true`
- Downloaded archive bytes: 30,946,172.
- Archive SHA-256: `B315CDE1C9B9D45008B5A7C4B2E1F87647659F09F74892AE3899C0005D5D6155`.
- Local extraction: `MINDsmall_dev/MINDsmall_dev/`.

MIND is research-only under the Microsoft Research License Terms. The archive
and extracted files are ignored by Git and must not be redistributed from this
repository.

The development split contains 42,416 news rows and 73,152 impressions. Its
observed impression interval is 2019-11-15 00:00:01 through 23:58:03 UTC.
There are 36,732 news rows with at least one linked Wikidata entity and 23,586
distinct linked QIDs in title or abstract annotations.

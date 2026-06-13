# Agentic Layer (Skills) Reference

::: xovis.skills.toolkit
    options:
      show_root_heading: true
      show_source: true

## Internal Evolution Tools

The SDK includes specialized skills for autonomous SDK evolution and schema discovery. These tools are used internally by the Xovis team to maintain parity with new hardware firmware versions.

### Schema Discovery (`discovery`)

The `SchemaAnalyst` skill performs semantic structural analysis of Xovis firmware schemas, identifying new features or field aliases using AI-assisted reasoning. These modules are excluded from the public SDK distribution to prevent version conflicts.

::: xovis.skills.langchain_adapter
::: xovis.skills.crewai_adapter

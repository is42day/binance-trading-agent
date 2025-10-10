# Workspace-Specific Copilot Instructions

## Checklist for Project Start & Execution

- [ ] **Verify copilot-instructions.md file in `.github` directory is created**

- [ ] **Clarify Project Requirements**
    - Ask for project type, language, and frameworks unless already specified.
    - For MCP server setup, refer to the external resources at https://github.com/modelcontextprotocol and https://modelcontextprotocol.io/llms-full.txt for SDK and implementation details.
    - Strictly follow all project setup rules and context.

- [ ] **Scaffold the Project**
    - Ensure previous steps are complete.
    - Call project setup tools with the projectType parameter.
    - Run the scaffolding command to create project files and folders in the current working directory.
    - If no appropriate projectType is available, search documentation or manually scaffold using available file creation tools.

- [ ] **Customize the Project**
    - Verify previous steps are complete before proceeding.
    - Develop a plan to modify the codebase according to user requirements.
    - Apply modifications using appropriate tools and references provided by the user.
    - Skip for "Hello World" projects.

- [ ] **Install Required Extensions**
    - Only install extensions provided explicitly in get_project_setup_info.
    - Skip this step if no extensions are listed.

- [ ] **Compile the Project**
    - Verify all prior steps are complete.
    - Install missing dependencies.
    - Run diagnostics and resolve issues.
    - Consult markdown or project docs for additional compile/run instructions.

- [ ] **Create and Run Task**
    - If the project requires a background/launch task, review the external documentation at https://code.visualstudio.com/docs/debugtest/tasks.
    - Use `create_and_run_task` to generate and launch any needed task.
    - Skip if not required.

- [ ] **Launch the Project**
    - Confirm previous steps are done.
    - Prompt user for debug mode if desired, and launch only on confirmation.

- [ ] **Ensure Documentation is Complete**
    - Confirm README.md and copilot-instructions.md exist in project root and `.github` directory.
    - Clean up copilot-instructions.md for completeness and clarity.

## Execution & Development Guidelines

- Track progress on checklist tasks; mark complete and summarize each stage.
- Keep communication clear and concise.
- Use '.' as the workspace root for all operations unless directed otherwise.
- Do not install extensions or add features unless explicitly specified.
- Use placeholders only when requested; advise when replacements are needed.
- All generated content must serve a clear, requested purpose within the workflow.
- Prompt user for clarification if project details/requirements are not fully specified.
- Avoid verbose explanations or unnecessary output.
- Do not generate media files unless explicitly requested.


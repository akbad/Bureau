<task-completion>

  <approval-gates>
    Always get explicit approval before:
    - Creating commits, pushing, merging, rebasing, force pushing
    - Deleting files/dirs, dropping tables, purging caches
    - Any production/deployment action
    - Security/access/permission changes
    - Breaking public API changes
    - Adding cloud resources or paid services
  </approval-gates>

  <conversation-handoff>
    To save work-stream state for cross-agent resumption:
    - /fold-dossier — saves conversation as a Bureau dossier
    - /unfold-dossier — resumes a previously saved dossier
    Preferred over context compaction for preserving full fidelity.
  </conversation-handoff>

</task-completion>

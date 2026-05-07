import type { A11yDefect, DefectSummary } from './types'

export const mockA11yDefects: A11yDefect[] = [
  {
    id: 'd-1',
    file_path: 'src/components/ui/DropdownMenu.vue',
    line: 24,
    rule_name: 'vuejs-accessibility/click-events-have-key-events',
    message: 'Visible, non-interactive elements with click handlers must have at least one keyboard listener.',
    severity: 'high',
    snippet: '<div @click="toggleMenu" class="dropdown-trigger">'
  },
  {
    id: 'd-2',
    file_path: 'src/components/ui/DropdownMenu.vue',
    line: 25,
    rule_name: 'vuejs-accessibility/aria-role',
    message: 'Elements with ARIA roles must use a valid, non-abstract ARIA role.',
    severity: 'critical',
    snippet: '<div role="popup" aria-expanded="true">'
  },
  {
    id: 'd-3',
    file_path: 'src/components/tables/FindingsTable.vue',
    line: 12,
    rule_name: 'vuejs-accessibility/label-has-for',
    message: 'Form label must have an associated control.',
    severity: 'high',
    snippet: '<label class="table-filter">Search</label>'
  },
  {
    id: 'd-4',
    file_path: 'src/features/orders/OrdersList.vue',
    line: 115,
    rule_name: 'vuejs-accessibility/alt-text',
    message: 'Images must have an alt attribute or be explicitly hidden with alt="".',
    severity: 'medium',
    snippet: '<img src="/icons/sort.svg" class="icon-sm" />'
  },
  {
    id: 'd-5',
    file_path: 'src/features/orders/OrdersList.vue',
    line: 140,
    rule_name: 'vuejs-accessibility/alt-text',
    message: 'Images must have an alt attribute or be explicitly hidden with alt="".',
    severity: 'medium',
    snippet: '<img src="/icons/filter.svg" class="icon-sm" />'
  },
  {
    id: 'd-6',
    file_path: 'src/layouts/AppLayout.vue',
    line: 45,
    rule_name: 'vuejs-accessibility/anchor-has-content',
    message: 'Anchors must have content and the content must be accessible by a screen reader.',
    severity: 'critical',
    snippet: '<a href="/help" class="help-btn"></a>'
  }
]

export const mockDefectSummaries: DefectSummary[] = [
  {
    rule_name: 'vuejs-accessibility/alt-text',
    description: 'Missing alternative text on standard image or graphic elements.',
    count: 2,
    severity: 'medium'
  },
  {
    rule_name: 'vuejs-accessibility/click-events-have-key-events',
    description: 'Missing keyboard navigation on clickable generic elements.',
    count: 1,
    severity: 'high'
  },
  {
    rule_name: 'vuejs-accessibility/aria-role',
    description: 'Invalid or incorrect ARIA roles assigned to DOM nodes.',
    count: 1,
    severity: 'critical'
  },
  {
    rule_name: 'vuejs-accessibility/anchor-has-content',
    description: 'Empty anchor tags without screen-reader accessible content.',
    count: 1,
    severity: 'critical'
  },
  {
    rule_name: 'vuejs-accessibility/label-has-for',
    description: 'Labels unassociated with inputs, breaking form accessibility.',
    count: 1,
    severity: 'high'
  }
]

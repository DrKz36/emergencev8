import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../../core/__tests__/helpers/dom-shim.js';

import { AuthAdminModule } from '../auth-admin-module.js';
import { api } from '../../../shared/api-client.js';

const noopClassList = {
  add: () => {},
  remove: () => {},
};

test('updateAllowlistTable flags revoked entries', () => {
  const module = new AuthAdminModule({ emit: () => {} }, {});
  module.tableBody = { innerHTML: '' };

  const items = [
    {
      email: 'active@example.com',
      role: 'member',
      note: 'Active user',
      password_updated_at: '2025-09-25T10:00:00Z',
    },
    {
      email: 'revoked@example.com',
      role: 'admin',
      note: 'Revoked access',
      revoked_at: '2025-09-25T10:00:00Z',
    },
  ];

  module.updateAllowlistTable(items);

  assert(module.tableBody.innerHTML.includes('auth-admin__row--revoked'));
  assert(module.tableBody.innerHTML.includes('auth-admin__status-badge--revoked'));
});

test('loadAllowlist applies filters and updates summary', async () => {
  const originalList = api.authAdminListAllowlist;
  const calls = [];
  api.authAdminListAllowlist = async (params = {}) => {
    calls.push(params);
    return {
      items: [
        {
          email: 'admin@example.com',
          role: 'admin',
          note: '',
          password_updated_at: null,
        },
      ],
      total: 1,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      status: params.status ?? 'active',
      query: params.query ?? '',
      has_more: false,
    };
  };

  try {
    const module = new AuthAdminModule({ emit: () => {} }, {});
    module.tableBody = { innerHTML: '' };
    module.summaryNode = { textContent: '' };
    module.paginationInfo = { textContent: '' };
    module.prevPageButton = { disabled: false };
    module.nextPageButton = { disabled: false };
    module.statusSelect = { value: 'active' };
    module.searchInput = { value: '' };
    module.messageNode = { textContent: '', classList: noopClassList };

    await module.loadAllowlist();

    module.status = 'revoked';
    module.statusSelect.value = 'revoked';
    await module.loadAllowlist();

    const lastCall = calls.at(-1) || {};
    assert.equal(lastCall.status, 'revoked');
    assert(module.summaryNode.textContent.includes('1'));
    assert(module.paginationInfo.textContent.includes('1'));
  } finally {
    api.authAdminListAllowlist = originalList;
  }
});

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { t } from '../i18n.js';

test('returns admin translations for supported locales', () => {
  assert.equal(t('admin.submit', { locale: 'fr' }), 'Enregistrer');
  assert.equal(t('admin.table_email', { locale: 'en' }), 'Email');
  assert.notEqual(t('admin.title', { locale: 'fr' }), 'admin.title');
  assert.notEqual(t('admin.title', { locale: 'en' }), 'admin.title');
});

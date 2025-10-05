#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Lire l'input JSON depuis stdin
let inputData = '';
process.stdin.on('data', chunk => {
  inputData += chunk;
});

process.stdin.on('end', () => {
  try {
    const input = JSON.parse(inputData);

    // Lire le fichier de style
    const stylePath = path.join(process.cwd(), '.claude', 'instructions', 'style-fr-cash.md');
    const styleContent = fs.readFileSync(stylePath, 'utf8');

    // Créer le contexte additionnel
    const output = {
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: `INSTRUCTIONS DE STYLE À SUIVRE ABSOLUMENT:\n\n${styleContent}\n\n---\n\nRESPECTE CES INSTRUCTIONS POUR TOUTE LA CONVERSATION.`
      }
    };

    console.log(JSON.stringify(output));
    process.exit(0);
  } catch (error) {
    // Si erreur, on laisse passer sans bloquer
    console.error(JSON.stringify({ error: error.message }));
    process.exit(0);
  }
});

import React from 'react';
const $ = React.createElement;

function inline(text) {
    return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, index) =>
        part.startsWith('**') ? $('strong', { key: index }, part.slice(2, -2)) :
        part.startsWith('`') ? $('code', { key: index }, part.slice(1, -1)) : part);
}

function body(blocks) {
    return blocks.map((block, index) => {
        if (block.type === 'code') return $('pre', { key: index, className: 'message-code' }, block.text);
        if (block.type === 'divider') return $('hr', { key: index });
        if (block.type === 'table') return $('div', { key: index, className: 'message-table' }, $('table', {},
            $('thead', {}, $('tr', {}, ...block.headers.map((cell, key) => $('th', { key }, ...inline(cell))))),
            $('tbody', {}, ...block.rows.map((row, key) => $('tr', { key }, ...row.map((cell, key) => $('td', { key }, ...inline(cell))))))));
        if (block.type === 'heading') return $('h4', { key: index }, ...inline(block.text));
        if (block.type === 'list') return $('ul', { key: index }, ...block.items.map((item, key) => $('li', { key }, ...inline(item))));
        return $('p', { key: index, className: 'message-paragraph' }, ...inline(block.text));
    });
}

function diagnostic(info) {
    return $('div', { className: 'error-diagnostic', role: 'alert' },
        $('strong', {}, info.title), $('p', { className: 'error-action' }, info.action),
        $('details', {}, $('summary', {}, 'Detalle técnico'), $('pre', {}, info.detail)));
}

export default function Modal({ setProps, name, is_open = false, question = {}, answer = {} }) {
    const dialog = React.useRef(null);
    React.useEffect(() => {
        if (is_open && !dialog.current.open) dialog.current.showModal();
        if (!is_open && dialog.current.open) dialog.current.close();
    }, [is_open]);
    const close = () => setProps({ is_open: false });
    const titleId = `dialog-${name}`;
    const messages = answer.messages?.length ? answer.messages : (answer.history || []);
    return $('dialog', { ref: dialog, className: 'modal', 'aria-labelledby': titleId, onClose: close,
        onClick: (event) => { if (event.target === dialog.current) dialog.current.close(); } },
        $('div', { className: 'modal-header' },
            $('h2', { className: 'modal-title', id: titleId }, `${name.toUpperCase()} · comunicación del núcleo`),
            $('button', { type: 'button', className: 'close', onClick: close, 'aria-label': 'Cerrar' }, 'Cerrar')
        ),
        $('div', { className: 'modal-content' },
            $('h3', {}, 'Objetivo original'), $('p', {}, question.goal || question.query || 'Esperando una tarea.'),
            question.query && question.query !== question.goal ? $('section', {},
                $('h3', {}, 'Solicitud actual'), $('p', {}, question.query)) : null,
            answer.error_info ? diagnostic(answer.error_info) : null,
            ...messages.map((entry, index) => $('article', { key: index, className: `kernel-message kernel-${entry.status || 'info'} ${entry.sender === name ? 'outgoing' : 'incoming'}` },
                $('div', { className: 'message-meta' },
                    $('strong', {}, entry.sender === 'system' ? 'MAGI · COORDINACIÓN' : entry.sender ? (entry.sender === name ? `${name.toUpperCase()} → CONSEJO` : `CONSEJO ← ${entry.sender.toUpperCase()}`) : name.toUpperCase()),
                    $('span', { className: `vote-badge vote-${entry.status || 'info'}` }, entry.label || 'Mensaje')),
                $('small', {}, `Paso ${entry.iteration || 1} · ${entry.phase} · ciclo ${entry.cycle || 1}${entry.at ? ` · ${entry.at.slice(11, 19)} UTC` : ''}`),
                ...(entry.error_info ? [] : body(entry.blocks || [{ type: 'paragraph', text: entry.text }])),
                entry.error_info ? diagnostic(entry.error_info) : null
            ))
        )
    );
}

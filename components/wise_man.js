import React from 'react';
const $ = React.createElement;

const colors = { yes: '#52e691', no: '#e76856', info: '#3caee0', conditional: '#ff8d00', error: '#ff6b64' };
const labels = { yes: 'Aprobado', no: 'Objeción', info: 'En espera', conditional: 'Con condiciones', error: 'Error' };

export default function WiseMan({ setProps, name, order_number, question_id = '0', answer = { id: '0', status: 'info' }, n_clicks = 0, runtime = '' }) {
    const processing = question_id !== answer.id;
    const stateLabel = processing ? answer.activity || 'Procesando…'
        : answer.error_info ? answer.error_info.title : answer.status === 'info' && answer.activity ? answer.activity : labels[answer.status];
    const secondaryActivity = !processing && answer.activity && answer.status !== 'info' && !answer.error;
    return $('button', {
        type: 'button', className: `wise-man ${name}`, onClick: () => setProps({ n_clicks: n_clicks + 1 }),
        'aria-label': `Ver propuestas y votos de ${name.toUpperCase()}${answer.error_info ? ` · ${answer.error_info.title}` : ''}`, 'aria-haspopup': 'dialog',
        title: answer.error_info ? `${answer.error_info.title}. ${answer.error_info.action}`
            : `${runtime} · ${stateLabel}${secondaryActivity ? ` · ${answer.activity}` : ''}`
    }, $('span', { className: `inner${processing ? ' processing' : ''}`, style: { background: colors[answer.status] || colors.error } },
        $('strong', {},
            $('span', { className: 'node-number', 'aria-hidden': true }, order_number),
            $('span', { className: 'node-name' }, name.toUpperCase()),
            $('span', { className: 'classic-number' }, ` · ${order_number}`)),
        $('span', { className: 'node-runtime' }, runtime),
        $('span', { className: 'node-state' }, stateLabel),
        secondaryActivity ? $('span', { className: 'node-activity' }, answer.activity) : null
    ));
}

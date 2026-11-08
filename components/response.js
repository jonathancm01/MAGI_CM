import React from 'react';
const $ = React.createElement;

function getStatusText(status) {
    if (status === 'info')
        return '情 報';

    if (status === 'yes')
        return '合 意';

    if (status === 'no')
        return '拒 絶';

    if (status === 'conditional')
        return '状 態';

    if (status === 'error')
        return '誤 差'

    throw new Error('Invalid status: ' + status);
}

function getStatusColor(status) {
    if (status === 'info')
        return '#3caee0';

    if (status === 'yes')
        return '#52e691';

    if (status === 'no')
        return '#a41413';

    if (status === 'conditional')
        return '#ff8d00';

    if (status === 'error')
        return '#ff6b64';

    throw new Error('Invalid status: ' + status);
}

export default function Response({ id, status, question_id, answer_id, text, translation = '' }) {
    text = text || getStatusText(status);
    const color = getStatusColor(status);

    let className = 'response';
    if (question_id !== answer_id)
        className += ' flicker';

    return $('div', { id, className, title: translation, 'aria-label': translation || text,
        style: { color, borderColor: color, '--caption-length': text.replace(/\s/g, '').length } },
        $('div', { className: 'inner', lang: 'ja' }, text)
    );
}

Response.defaultProps = {
    status: 'info',
    question_id: 0,
    answer_id: 0
};

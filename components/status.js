import React from 'react';
const $ = React.createElement;

export default function Status({ extention }) {
    const phases = { IDLE: 'ESPERA', ANALYSIS: 'ANALISIS', VOTING: 'VOTACION', READY: 'LISTO', BLOCKED: 'OBJECION',
        EXECUTION: 'EJECUCION', REVIEW: 'REVISION', DONE: 'TERMINADO', CHANGES_REQUESTED: 'REVISAR', CANCELLED: 'CANCELADO',
        INTERRUPTED: 'INTERRUMPIDO', RESTORED: 'RECUPERADO', ERROR: 'ERROR', LIMIT: 'LIMITE' };
    const extentionLabel = `FASE:${phases[extention] || extention}`;

    return $('div', { className: 'system-status' },
        $('div', {}, 'CODE:473'),
        $('div', {}, 'FILE:MAGI_SYS'),
        $('div', {}, extentionLabel),
        $('div', {}, `EX_MODE:${extention === 'EXECUTION' ? 'ON' : 'OFF'}`),
        $('div', {}, 'PRIORITY:AAA')
    );
}

Status.defaultProps = {
    extention: 'IDLE'
};

import React from "react";
const $ = React.createElement;

export default function Magi({ id, children, variant = 'classic' }) {
    return $('div', { id, className: `magi${variant === 'triangular' ? ' magi--triangular' : ''}` },
        $('div', { className: 'orbit', 'aria-hidden': true }),
        $('div', { className: 'connection casper-balthasar' }),
        $('div', { className: 'connection casper-melchior' }),
        $('div', { className: 'connection balthasar-melchior' }),
        ...children,
        $('div', { className: 'title' }, 'MAGI')
    );
}

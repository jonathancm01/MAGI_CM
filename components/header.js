import React from "react";
const $ = React.createElement;

export default function Header({ id, side, title, translation = '' }) {
    const className = `header ${side}`;

    return $('div', { id, className, title: translation, 'aria-label': translation || title },
        $('hr', {}),
        $('hr', {}),
        $('span', { lang: 'ja', style: { '--caption-length': title.length } }, title),
        $('hr', {}),
        $('hr', {})
    );
}

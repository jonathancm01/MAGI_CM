(() => {
    const instance = document.querySelector('meta[name="magi-instance"]');
    if (!instance) return;

    let connection;
    const connect = () => {
        if (!connection) {
            connection = new EventSource(`/_magi/browser?instance=${encodeURIComponent(instance.content)}`);
        }
    };
    window.addEventListener('pagehide', () => {
        if (connection) connection.close();
        connection = null;
    });
    window.addEventListener('pageshow', connect);
    connect();
})();

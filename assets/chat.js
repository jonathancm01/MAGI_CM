(() => {
    function connect() {
        const conversation = document.getElementById('conversation');
        const mode = document.querySelector('#request-mode [role="combobox"]');
        const tools = document.getElementById('workspace-tools');
        const openTools = document.getElementById('open-configuration');
        const closeTools = document.getElementById('close-configuration');
        const search = document.getElementById('nav-search');
        const navigation = document.getElementById('project-list');
        const query = document.getElementById('query');
        const start = document.getElementById('start');
        const latest = document.getElementById('jump-latest');
        const expand = document.getElementById('expand-chat');
        if (!conversation || !mode || !tools || !openTools || !closeTools ||
            !search || !navigation || !query || !start || !latest || !expand) return false;
        mode.setAttribute('aria-label', 'Modo de solicitud');
        search.setAttribute('aria-keyshortcuts', 'Control+k Meta+k');
        openTools.addEventListener('click', () => { if (!tools.open) tools.showModal(); });
        closeTools.addEventListener('click', () => tools.close());

        const tabs = Array.from(tools.querySelectorAll('[data-settings-tab]'));
        function selectTab(tab) {
            tabs.forEach(item => {
                const selected = item === tab;
                item.setAttribute('aria-selected', String(selected));
                item.tabIndex = selected ? 0 : -1;
            });
            tools.querySelectorAll('[data-settings-panel]').forEach(panel => {
                panel.hidden = panel.dataset.settingsPanel !== tab.dataset.settingsTab;
            });
        }
        tabs.forEach((tab, index) => {
            tab.addEventListener('click', () => selectTab(tab));
            tab.addEventListener('keydown', event => {
                let next;
                if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
                if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
                if (event.key === 'Home') next = 0;
                if (event.key === 'End') next = tabs.length - 1;
                if (next !== undefined) {
                    event.preventDefault();
                    selectTab(tabs[next]);
                    tabs[next].focus();
                }
            });
        });

        const normalized = value => value.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        function filterChats() {
            const term = normalized(search.value.trim());
            let count = 0;
            navigation.querySelectorAll('.project-group').forEach(group => {
                const projectMatches = normalized(group.dataset.projectName || '').includes(term);
                let visible = 0;
                group.querySelectorAll('[data-chat-title]').forEach(row => {
                    row.hidden = !!term && !projectMatches && !normalized(row.dataset.chatTitle).includes(term);
                    if (!row.hidden) visible++;
                });
                group.hidden = !visible;
                count += visible;
            });
            document.getElementById('nav-search-status').textContent = !term ? '' : count
                ? count + (count === 1 ? ' chat encontrado' : ' chats encontrados')
                : 'Sin coincidencias. Prueba otro nombre.';
        }
        search.addEventListener('input', filterChats);
        search.addEventListener('search', filterChats);
        new MutationObserver(filterChats).observe(navigation, {childList: true, subtree: true});

        expand.addEventListener('click', () => {
            const expanded = document.querySelector('.workspace-pane').classList.toggle('workspace-pane--reading');
            expand.setAttribute('aria-pressed', String(expanded));
            expand.textContent = expanded ? 'Restaurar MAGI' : 'Ampliar chat';
        });
        let focusSearchAfterExpand = false;
        new MutationObserver(() => {
            if (focusSearchAfterExpand && document.getElementById('toggle-sidebar').getAttribute('aria-expanded') === 'true') {
                focusSearchAfterExpand = false;
                search.focus();
            }
        }).observe(document.getElementById('desktop-shell'), {attributes: true, attributeFilter: ['class']});
        document.addEventListener('keydown', event => {
            if (!(event.ctrlKey || event.metaKey) || event.isComposing || event.altKey) return;
            if (event.key.toLowerCase() === 'k' && !document.querySelector('dialog[open]')) {
                event.preventDefault();
                const toggle = document.getElementById('toggle-sidebar');
                if (toggle.getAttribute('aria-expanded') === 'false') {
                    focusSearchAfterExpand = true;
                    toggle.click();
                } else search.focus();
            } else if (event.key === ',') {
                event.preventDefault();
                if (!tools.open && !document.querySelector('dialog[open]')) openTools.click();
            } else if (event.key === 'Enter' && event.target === query && !start.disabled) {
                event.preventDefault();
                start.click();
            }
        });

        // Routine acknowledgements should not permanently reduce the reading area.
        ['notice', 'configuration-notice'].forEach(id => {
            const notice = document.getElementById(id);
            let timeout;
            new MutationObserver(() => {
                clearTimeout(timeout);
                notice.hidden = false;
                if (/^(Solicitud enviada|Configuración guardada|Ejecución iniciada|Revisión iniciada|Cancelación solicitada|Chat enviado|Chat restaurado)/.test(notice.textContent)) {
                    timeout = setTimeout(() => { notice.hidden = true; }, 6000);
                }
            }).observe(notice, {childList: true, subtree: true, characterData: true});
        });
        let chat = conversation.dataset.chat;
        let following = true;
        function scrollToLatest() {
            conversation.scrollTop = conversation.querySelector('.empty-chat') ? 0 : conversation.scrollHeight;
            following = true;
            latest.hidden = true;
        }
        latest.addEventListener('click', scrollToLatest);
        conversation.addEventListener('scroll', () => {
            following = conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight < 80;
            latest.hidden = following;
        }, { passive: true });
        new MutationObserver(() => {
            const changed = conversation.dataset.chat !== chat;
            chat = conversation.dataset.chat;
            if (changed || following) {
                scrollToLatest();
            } else {
                latest.hidden = false;
            }
        }).observe(conversation, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-chat'] });
        scrollToLatest();
        filterChats();
        return true;
    }
    const waiting = new MutationObserver(() => {
        if (connect()) waiting.disconnect();
    });
    if (!connect()) waiting.observe(document.documentElement, { childList: true, subtree: true });
})();

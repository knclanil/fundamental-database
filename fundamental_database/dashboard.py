"""Read-only local research dashboard; start with `streamlit run dashboard_app.py`."""
import os
import streamlit as st
from .storage import connect
from .rankings import rank_companies


def main():
    st.set_page_config(page_title='Fundamental Database', layout='wide')
    st.title('Fundamental Database')
    path = st.sidebar.text_input('SQLite database', os.getenv('FUNDAMENTALS_DB', 'data/fundamentals.sqlite'))
    cutoff = st.sidebar.date_input('As-of filing date').isoformat()
    search = st.sidebar.text_input('Company / ticker filter')
    db = connect(path)
    try:
        rows = rank_companies(db, as_of=cutoff)
        if search:
            rows = [r for r in rows if search.lower() in (r['name'] + ' ' + (r['ticker'] or '')).lower()]
        st.metric('Ranked companies', len(rows))
        st.dataframe([{k: v for k, v in row.items() if k != 'metrics'} for row in rows],
                     use_container_width=True, hide_index=True)
        if rows:
            choices = {f"{r['ticker']} | {r['name']} | {r['period_end']}": r for r in rows}
            selected = choices[st.selectbox('Inspect metrics', list(choices))]
            st.json(selected)
        else:
            st.info('No ranked records yet. Run the SEC collection workflow and download its database artifact.')
    finally:
        db.close()

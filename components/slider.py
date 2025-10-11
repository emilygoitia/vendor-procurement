import streamlit as st


def render_styled_slider(
    label,
    min_value,
    max_value,
    default_value,
    step=1,
    help=None,
    key=None,
    disabled=False,
):
    with st.container():
        st.write("<div class='styled-slider' />", unsafe_allow_html=True)
        slider = st.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            value=default_value,
            step=step,
            help=help,
            key=key,
            disabled=disabled,
        )
        return slider

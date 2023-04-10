from dash import html


def create_page_heading(title):
    return html.H1(
        title,
        className='page-heading'
    )

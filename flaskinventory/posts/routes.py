from flask import (Blueprint, render_template, url_for, flash, redirect, request, abort)
from flask_login import login_user, current_user, logout_user, login_required
from flaskinventory.posts.forms import PostForm
from flaskinventory import dgraph

posts = Blueprint('posts', __name__)

@posts.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post_data = {'title': form.title.data, 'content': form.content.data, 'author': [
            {'uid': current_user.id}]}
        response = dgraph.create_post(post_data)
        flash(f'New post published!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html', title='New Post', form=form,
                           legend="New Post")


@posts.route("/post/<string:post_id>")
def post(post_id):
    post = dgraph.get_post(post_id)
    if post:
        return render_template('post.html', title=post.get('title'), post=post)
    else:
        return abort(404)


@posts.route("/post/<string:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = dgraph.get_post(post_id)
    if post:
        if post['author']['uid'] != current_user.id:
            return abort(403)
        form = PostForm()
        if form.validate_on_submit():
            changes = {'title': form.title.data, 'content': form.content.data}
            dgraph.update_entry(post_id, changes)
            flash('Your post has been updated!', 'success')
            return redirect(url_for('posts.post', post_id=post_id))
        elif request.method == 'GET':
            form.title.data = post['title']
            form.content.data = post['content_raw']

        return render_template('create_post.html', title="Update Post", post=post,
                               form=form, legend="Update Post")
    else:
        return abort(404)


@posts.route("/post/<string:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = dgraph.get_post(post_id)
    if post:
        if post['author']['uid'] != current_user.id:
            return abort(403)

        dgraph.delete_entry(post_id)
        flash('Your post has been deleted!', 'success')
        return redirect(url_for('main.home'))

    else:
        return abort(404)


@posts.route('/user/<string:username>')
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user, posts, total, pages = dgraph.list_user_posts(username=username)
    pages = range(1, pages+1)
    return render_template('home.html', user=user, posts=posts, pages=pages, current_page=page)


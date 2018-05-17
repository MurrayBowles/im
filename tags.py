""" tag operations """

import db
import difflib
from ie_fs import IETagType


def find_text_binding(session, text, fs_tag_source):
    """ Return [text, FsTagBinding, FsItemTagSource, DbTag id]. """
    mapping = db.FsTagMapping.find(session, fs_tag_source, text)
    if mapping is not None:
        # <text> is mapped in <fs_tag_source>
        return [
            text, mapping.binding, db.FsItemTagSource.FSTS, mapping.db_tag]
    mapping = db.FsTagMapping.find(session, db.global_tag_source, text)
    if mapping is not None:
        # <text> is mapped in <global_tag_source>
        return [
            text, mapping.binding, db.FsItemTagSource.GLOBTS, mapping.db_tag]
    db_tag = db.DbTag.find_expr(session, text)
    if db_tag is not None:
        # <text> occurs in the DbTag database
        return [text, db.FsTagBinding.BOUND, db.FsItemTagSource.DBTAG, db_tag]
    return [text, db.FsTagBinding.UNBOUND, db.FsItemTagSource.NONE, None]


def tag_text_binding(session, text, bases, fs_tag_source):
    """ Return [text, FsTagBinding, FsItemTagSource, DbTag id]. """
    results = []
    if text.find('|') == -1:
        # <text> is a flat tag
        # try <base>|<text> for each suggested base in ie_tag.bases
        if bases is not None:
            bases = bases.split(',')
            for base in bases:
                base = base.strip()
                t = base + '|' + text
                results.append(find_text_binding(session, t, fs_tag_source))

        # try just <text>
        flat_result = find_text_binding(session, text, fs_tag_source)
        if (flat_result[3] is not None and
            flat_result[3].parent is not None and
            flat_result[3].parent.text not in bases
        ):
            # DbTag has a parent, and it's not one of the proposed bases:
            # demote from BOUND to SUGGESTED
            if flat_result[1] == db.FsTagBinding.BOUND:
                flat_result[1] = db.FsTagBinding.SUGGESTED
    else:
        # <text> is a hierarchical tag
        flat_result = find_text_binding(session, text, fs_tag_source)
    results.append(flat_result)

    results.sort(key = lambda x: x[1], reverse=True)
    result = results[0]
    return result


def word_list_bindings(session, word_list, bases, fs_tag_source):
    """ Return [(relative idx range, [text, binding, source, db_tag])]. """
    def partition_words(pfx, word_list, partitions):
        partitions.append(pfx + [word_list])
        if len(word_list) > 1:
            for x in range(1, len(word_list)):
                partition_words(
                    pfx + [word_list[0:x]], word_list[x:], partitions)
    partitions = []
    partition_words([], word_list, partitions)

    scores = []
    for partition in partitions:
        bindings = []
        total_score = 1
        have_unbound_multiword = False
        for wl in partition:
            text = ' '.join(wl)
            binding = tag_text_binding(
                session, text, bases, fs_tag_source)
            if binding[1] == db.FsTagBinding.UNBOUND and len(wl) > 1:
                have_unbound_multiword = True
            bindings.append(binding)
            total_score += binding[1].value # UNBOUND | SUGGESTED | BOUND
        if have_unbound_multiword:
            # don't consider a partition that has unbound multi-word elements
            total_score = 0
        scores.append((total_score / len(partition), partition, bindings))
    scores.sort(key = lambda x: x[0], reverse=True) # sort by descending score

    results = []
    score = scores[0]
    idx = 0
    for wl, binding in zip(score[1], score[2]):
        r = range(idx, idx + len(wl))
        results.append((r, binding))
        idx += len(wl)
    return results


def _bind_fs_item_tags(session, item, fs_tag_source):
    """ (Re)Bind item.item_tags based on fs_tag_source.

        (1) leaves source==DIRECT tags untouched
        (2) binds all other tags, ignoring their current binding
        (3) assumes that there are no auto-groupings, only user-assigned ones
    """
    if item.name.find("01_03_92_15_GILMAN-001") != -1:
        pass
    idx = 0
    while idx < len(item.item_tags):
        fs_tag = item.item_tags[idx]
        if fs_tag.type == db.FsTagType.TAG:
            binding = tag_text_binding(
                session, fs_tag.text, fs_tag.bases, fs_tag_source)
            fs_tag.set_binding(
                source=binding[2], binding=binding[1], db_tag=binding[3])
            idx += 1
        else: # db.FsTagType.WORD
            word_list = [fs_tag.text]
            base_idx = idx
            while True:
                idx += 1
                if idx >= len(item.item_tags): break
                fs_tag = item.item_tags[idx]
                if fs_tag.type != db.FsTagType.WORD: break
                word_list.append(fs_tag.text)
            results = word_list_bindings(
                session, word_list, fs_tag.bases, fs_tag_source)
            for range, binding in results:
                for offset in range:
                    fs_tag = item.item_tags[base_idx + offset]
                    fs_tag.set_binding(
                        source=binding[2],
                        binding=binding[1], db_tag=binding[3])
                db.FsItemTag.add_grouping(item, range)
            pass


def add_fs_item_note(session, item, ie_tag):
    """ Add a Note to <item>. """
    pass


def _adjust_db_item_tags(session, fs_item, old_tag_set, new_tag_set):
    """ Adjust fs_item's DbItem's tags based on the changes from old to new """
    db_item = fs_item.db_item()
    if db_item is None:
        return
    deleted_tags = old_tag_set - new_tag_set
    added_tags = new_tag_set - old_tag_set
    if len(deleted_tags) > 0:
        # recalculate db_item's EXTERNAL tags by ORing the tags of its FsItems
        new_tags = set()
        for fsi in db_item.fs_items():
            for it in fsi.item_tags:
                if it.db_tag is not None:
                    new_tags.add(it.db_tag)
        pass
        for it in db_item.tags:
            if ((db.TagFlags.EXTERNAL & it.flags) != 0
            and it.tag not in new_tags):
                db_item.mod_tag_flags(
                    session, it.tag, del_flags=db.TagFlags.EXTERNAL)
        for t in new_tags:
            db_item.mod_tag_flags(
                session, t, add_flags=db.TagFlags.EXTERNAL)
    else:
        # add added_tags to db_item's tags
        for db_tag in added_tags:
            db_item.mod_tag_flags(
                session, db_tag, add_flags=db.TagFlags.EXTERNAL)


def init_fs_item_tags(session, item, ie_tags, fs_tag_source):
    """ Initialize item.item_tags from ie_tags based on fs_tag_source. """
    idx = 0
    for ie_tag in ie_tags:
        if ie_tag.type == IETagType.NOTE:
            add_fs_item_note(session, item, ie_tag)
        else:
            if ie_tag.is_tag():
                type = db.FsTagType.TAG
                text = ie_tag.text.replace('/', '|')
                # 'meta/misc/cool' => 'meta|misc|cool'
                # FIXME: this fix is specific to Corbett image tags,
                # so it should be done in ie_fs.py
            else:
                assert ie_tag.type == IETagType.WORD
                type = db.FsTagType.WORD
                text = ie_tag.text
            item_tag = db.FsItemTag.insert(session,
                item, idx, type=type, text=text, bases=ie_tag.bases)
            idx += 1
    _bind_fs_item_tags(session, item, fs_tag_source)
    new_db_tag_set = item.db_tag_set()
    _adjust_db_item_tags(session, item, set(), new_db_tag_set)
    pass


def update_fs_item_tags(session, fs_item, ie_tags, fs_tag_source):
    """ Update fs_item.item_tags from ie_tags based on fs_tag_source.

        Called when an external fs_item is re-scanned to re-evaluate its tags:
        1) compare the ie_tags against the FsItemTags to see if there are changes
        2) if so, deal with them (TODO: gracefully if possible)
    """
    old_db_tag_set = fs_item.db_tag_set()
    old_diff_tups = [
        fs_t.diff_tup()
        for fs_t in fs_item.item_tags if fs_t.diff_tup()[0] != 'n']
    new_diff_tups = [
        ie_t.diff_tup() for ie_t in ie_tags]
    if old_diff_tups == new_diff_tups:
        # no change in external tags
        return

    # diff the imported tags with the current ones
    # TODO: flag when user-defined groupings are destroyed
    s = difflib.SequenceMatcher(None, old_diff_tups, new_diff_tups)
    item_tags = fs_item.item_tags
    opcodes = s.get_opcodes()
    opcodes.reverse()
    got_changes = False
    for op in opcodes:
        act, old_start, old_stop, new_start, new_stop = op
        if act == 'equal':
            continue
        if not got_changes:
            got_changes = True
            # remove any auto-assigned word groupings
            for item_tag in item_tags:
                if not item_tag.user_grouping:
                    item_tag.del_grouping()

        # a user-assigned word-grouping spans or extends into the change
        if (
            old_start > 0
            and item_tags[old_start - 1].user_grouping
            and old_diff_tups[old_start - 1][0] == 'w'
            and item_tags[old_start - 1].last_idx >= old_start
        ):
            db.FsItemTag.del_grouping(item_tags[old_start - 1])
        if (
            old_stop < len(item_tags)
            and item_tags[old_stop].user_grouping
            and old_diff_tups[old_stop][0] == 'w'
            and item_tags[old_stop].first_idx < old_stop
        ):
            db.FsItemTag.del_grouping(item_tags[old_stop])

        # TODO a user-assigned word-grouping abuts the change
        # and the affected region will start(end) with a word after the change

        if act != 'insert':
            # delete old_start:old_stop
            for idx in range(old_start, old_stop):
                item_tags[idx].delete(session)
            pass
        if act != 'delete':
            # insert new_start:new_stop at old_start
            offset = 0
            for t in new_diff_tups[new_start:new_stop]:
                db.FsItemTag.insert(session,
                    fs_item, old_start + offset,
                    db.FsTagType.WORD if t[0] == 'w' else db.FsTagType.TAG,
                    t[1], t[2])
            pass

    if got_changes:
        try:
            _bind_fs_item_tags(session, fs_item, fs_tag_source)
        except Exception as ed:
            pass
        new_db_tag_set = fs_item.db_tag_set()
        _adjust_db_item_tags(session, fs_item, old_db_tag_set, new_db_tag_set)
    pass


def rebind_fs_item_tags(session, item, fs_tag_source):
    """ Update item.item_tags based on fs_tag_source.

        Called when a tag or tag mapping is added/deleted/modified:
        (1) leaves source==DIRECT tags untouched
        (2) rebinds all other tags, ignoring their current binding
    """
    old_db_tag_set = item.db_tag_set()
    _bind_fs_item_tags(session, item, fs_tag_source)
    new_db_tag_set = item.db_tag_set()
    _adjust_db_item_tags(session, item, old_db_tag_set, new_db_tag_set)
    pass


def _on_tag_change(session, text):
    """ Schedule a task to recalculate all FsItemTag bindings involving <text>.

        called when a DbTag or FsTagMapping is changed
        <text> is a leaf tag string,
            e.g. 'Green Day' if the eDbTag 'band}Green Day' was changed
    """
    db.TagChange.add(session, text)
    pass


def on_db_tag_added(session, db_tag):
    """ Schedule a task to add auto-FsItemTags to matching FsItems.

        called when a DbTag is added, renamed, or un-deprecated
    """
    _on_tag_change(session, db_tag.name)


def on_db_tag_removed(session, db_tag):
    """ Schedule a task to remove auto-FsItemTags from matching FsItems.

        called when a DbTag is renamed or deprecated
    """
    _on_tag_change(session, db_tag.name)


def on_fs_tag_mapping_added(session, mapping):
    """ Schedule a task to add auto-FsItemTags for matching FsItems.

        called when an FsTagMapping is added or its .binding is changed
    """
    _on_tag_change(session, mapping.leaf_text())


def on_fs_tag_mapping_removed(session, mapping):
    """ Schedule a task to remove auto-FsItemTags from matching FsItems.

        called when an FsTagMapping is deleted or its .binding is changed
    """
    _on_tag_change(session, mapping.leaf_text())

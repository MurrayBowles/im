''' tag operations '''

import db
from ie_fs import IETagType

def find_text_binding(session, text, fs_tag_source):
    ''' return [text, FsTagBinding, FsItemTagSource, DbTag id] '''
    mapping = db.FsTagMapping.find(session, fs_tag_source, text)
    if mapping is not None:
        # <text> is mapped in <fs_tag_source>
        return [text, mapping.binding, db.FsItemTagSource.FSTS, mapping.db_tag]
    mapping = db.FsTagMapping.find(session, db.global_tag_source, text)
    if mapping is not None:
        # <text> is mapped in <global_tag_source>
        return [text, mapping.binding, db.FsItemTagSource.GLOBTS, mapping.db_tag]
    db_tag = db.DbTag.find_expr(session, text)
    if db_tag is not None:
        # <text> occurs in the DbTag database
        return [text, db.FsTagBinding.BOUND, db.FsItemTagSource.DBTAG, db_tag]
    return [text, db.FsTagBinding.UNBOUND, db.FsItemTagSource.NONE, None]

def find_ie_tag_binding(session, ie_tag, text, fs_tag_source):
    ''' return [text, FsTagBinding, FsItemTagSource, DbTag id] '''

    results = []
    if text.find('|') == -1:
        # <text> is a flat tag
        # try <base>|<text> for each suggested base in ie_tag.bases
        if ie_tag.bases is not None:
            bases = ie_tag.bases.split(',')
            for base in bases:
                base = base.strip()
                t = base + '|' + text
                results.append(find_text_binding(session, t, fs_tag_source))

        # try just <text>
        flat_result = find_text_binding(session, text, fs_tag_source)
        if (flat_result[3] is not None and
            flat_result[3].parent is not None and
            flat_result[3].parent.text not in ie_tag.bases
        ):
            # DbTag has a parent, and it's not one of the proposed bases:
            # demote from BOUND to SUGGESTED
            if flat_result[1] == db.FsTagBinding.BOUND:
                flat_result[1] = db.FsTagBinding.SUGGESTED
    else:
        # <text> is a hierarchical tag
        flat_result = result = find_text_binding(session, text, fs_tag_source)
    results.append(flat_result)

    results.sort(key = lambda x: x[1], reverse=True)
    result = results[0]
    return result

def add_word_fs_item_tags(session, item, base_idx, words, fs_tag_source):
    ''' add db.FsItemTags to <item>.tags[<base_idx>...], of type WORD '''
    def partition_words(pfx, words, partitions):
        partitions.append(pfx + [words])
        if len(words) > 1:
            for x in range(1, len(words)):
                partition_words(pfx + [words[0:x]], words[x:], partitions)
    partitions = []
    partition_words([], words, partitions)
    results = []
    for partition in partitions:
        bindings = []
        total_score = 1
        have_unbound_multiword = False
        for ie_elt_list in partition:
            text = ''
            sep = ''
            for ie_elt in ie_elt_list:
                text += sep + ie_elt.text
                sep = ' '
            binding = find_ie_tag_binding(
                session, ie_elt_list[0], text, fs_tag_source)
            if binding[1] == db.FsTagBinding.UNBOUND and len(ie_elt_list) > 1:
                have_unbound_multiword = True
            bindings.append(binding)
            total_score += binding[1].value # UNBOUND | SUGGESTED | BOUND
        if have_unbound_multiword:
            # don't consider a partition that has unbound multi-word elements
            total_score = 0
        results.append((total_score / len(partition), partition, bindings))
    results.sort(key = lambda x: x[0], reverse=True) # sort by the score
    result = results[0]
    idx = 0
    for ie_tag_list, binding in zip(result[1], result[2]):
        elt_base_idx = idx
        first_idx = base_idx + elt_base_idx
        last_idx = first_idx + len(ie_tag_list) - 1
        for ie_tag in ie_tag_list:
            item_tag = db.FsItemTag.add(session,
                item, base_idx + idx, (first_idx, last_idx),
                type=db.FsTagType.WORD, text=ie_tag.text, bases=words[0].bases,
                binding=binding[1], source=binding[2], db_tag=binding[3])
            idx += 1
    pass

def add_tag_fs_item_tag(session, item, idx, ie_tag, fs_tag_source):
    ''' add a db.FsItemTag to <item>.tags[<idx>], of type TAG '''
    text = ie_tag.text.replace('/', '|') # 'meta/misc/cool' => 'meta|misc|cool'
    binding = find_ie_tag_binding(session, ie_tag, text, fs_tag_source)
    item_tag = db.FsItemTag.add(session,
        item, idx, (idx, idx),
        type=db.FsTagType.TAG, text=text, bases=ie_tag.bases,
        binding=binding[1], source=binding[2], db_tag=binding[3])
    pass

def add_fs_item_note(session, item, ie_tag):
    ''' add a Note to <item> '''
    pass

def init_fs_item_tags(session, item, ie_tags, fs_tag_source):
    idx = 0
    ie_tag_iter = iter(ie_tags)
    # FIXME: what a mess! this would be easier to code in C
    try:
        ie_tag = next(ie_tag_iter)
        while True:
            if ie_tag.type in {IETagType.AUTO, IETagType.BASED, IETagType.UNBASED}:
                add_tag_fs_item_tag(session, item, idx, ie_tag, fs_tag_source)
                idx += 1
                ie_tag = next(ie_tag_iter)
            elif ie_tag.type == IETagType.WORD:
                words = [ie_tag]
                base_idx = idx
                done = False
                while True:
                    try:
                        idx += 1
                        ie_tag = next(ie_tag_iter)
                        if ie_tag.type != IETagType.WORD:
                            break
                        words.append(ie_tag)
                    except StopIteration:
                        done = True
                        break
                add_word_fs_item_tags(session, item, base_idx, words, fs_tag_source)
                if done:
                    break
            else:
                assert ie_tag.type == IETagType.NOTE
                add_fs_item_note(session, item, ie_tag)
                ie_tag = next(ie_tag_iter)
    except StopIteration:
        pass
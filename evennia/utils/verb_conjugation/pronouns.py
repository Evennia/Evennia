"""
English pronoun mapping between 1st/2nd person and 3rd person perspective (and vice-versa).

This file is released under the Evennia regular BSD License.
(Griatch 2021) - revised by InspectorCaracal 2022

Pronouns are words you use instead of a proper name, such as 'him', 'herself', 'theirs' etc. These
look different depending on who sees the outgoing string. This mapping maps between 1st/2nd case and
the 3rd person case and back. In some cases, the mapping is not unique; it is assumed the system can
differentiate between the options in some other way.


====================  =======  ========  ==========  ==========  ===========
viewpoint/pronouns    Subject  Object    Possessive  Possessive  Reflexive
                      Pronoun  Pronoun   Adjective   Pronoun     Pronoun
====================  =======  ========  ==========  ==========  ===========
1st person              I        me        my         mine       myself
1st person plural       we       us        our        ours       ourselves
2nd person              you      you       your       yours      yourself
2nd person plural       you      you       your       yours      yourselves

3rd person male         he       him       his        his        himself
3rd person female       she      her       her        hers       herself
3rd person neutral      it       it        its        its        itself
3rd person plural       they     them      their      theirs     themselves
====================  =======  ========  ==========  ==========  ===========
"""
from evennia.utils.utils import copy_word_case, is_iter

DEFAULT_PRONOUN_TYPE = "subject pronoun"
DEFAULT_VIEWPOINT = "2nd person"
DEFAULT_GENDER = "neutral"

PRONOUN_TYPES = [
    "subject pronoun",
    "object pronoun",
    "possessive adjective",
    "possessive pronoun",
    "reflexive pronoun",
]
VIEWPOINTS = ["1st person", "2nd person", "3rd person"]
GENDERS = ["male", "female", "neutral", "plural"]

PRONOUN_MAPPING = {
    "1st person": {
        "subject pronoun": {
            "neutral": "I",
            "plural": "we",
        },
        "object pronoun": {
            "neutral": "me",
            "plural": "us",
        },
        "possessive adjective": {
            "neutral": "my",
            "plural": "our",
        },
        "possessive pronoun": {
            "neutral": "mine",
            "plural": "ours",
        },
        "reflexive pronoun": {
            "neutral": "myself",
            "plural": "ourselves"
        }
    },
    "2nd person": {
        "subject pronoun": {
            "neutral": "you",
        },
        "object pronoun": {
            "neutral": "you",
        },
        "possessive adjective": {
            "neutral": "your",
        },
        "possessive pronoun": {
            "neutral": "yours",
        },
        "reflexive pronoun": {
            "neutral": "yourself",
            "plural": "yourselves",
        }
    },
    "3rd person": {
        "subject pronoun": {
            "male": "he",
            "female": "she",
            "neutral": "it",
            "plural": "they"
        },
        "object pronoun": {
            "male": "him",
            "female": "her",
            "neutral": "it",
            "plural": "them"
        },
        "possessive adjective": {
            "male": "his",
            "female": "her",
            "neutral": "its",
            "plural": "their"
        },
        "possessive pronoun": {
            "male": "his",
            "female": "hers",
            "neutral": "its",
            "plural": "theirs",
        },
        "reflexive pronoun": {
            "male": "himself",
            "female": "herself",
            "neutral": "itself",
            "plural": "themselves",
        },
    }
}

PRONOUN_TABLE = {
    "I": (
            "1st person",
            ("neutral", "male", "female"),
            "subject pronoun"
        ),
    "me": (
            "1st person",
            ("neutral", "male", "female"),
            "object pronoun"
        ),
    "my": (
            "1st person",
            ("neutral", "male", "female"),
            "possessive adjective"
        ),
    "mine": (
            "1st person",
            ("neutral", "male", "female"),
            "possessive pronoun"
        ),
    "myself": (
            "1st person",
            ("neutral", "male", "female"),
            "reflexive pronoun"
        ),

    "we": (
            "1st person",
            "plural",
            "subject pronoun"
        ),
    "us": (
            "1st person",
            "plural",
            "object pronoun"
        ),
    "our": (
            "1st person",
            "plural",
            "possessive adjective"
        ),
    "ours": (
            "1st person",
            "plural",
            "possessive pronoun"
        ),
    "ourselves": (
            "1st person",
            "plural",
            "reflexive pronoun"
        ),
    "you": (
            "2nd person",
            ("neutral", "male", "female", "plural"),
            ("subject pronoun", "object pronoun")
        ),
    "your": (
            "2nd person",
            ("neutral", "male", "female", "plural"),
            "possessive adjective"
        ),
    "yours": (
            "2nd person",
            ("neutral", "male", "female", "plural"),
            "possessive pronoun"
        ),
    "yourself": (
            "2nd person",
            ("neutral", "male", "female"),
            "reflexive pronoun"
        ),
    "yourselves": (
            "2nd person",
            "plural",
            "reflexive pronoun"
        ),
    "he": (
            "3rd person",
            "male",
            "subject pronoun"
        ),
    "him": (
            "3rd person",
            "male",
            "object pronoun"
        ),
    "his":(
            "3rd person",
            "male",
            ("possessive pronoun","possessive adjective"),
        ),
    "himself": (
            "3rd person",
            "male",
            "reflexive pronoun"
        ),
    "she": (
            "3rd person",
            "female",
            "subject pronoun"
        ),
    "her": (
            "3rd person",
            "female",
            ("object pronoun", "possessive adjective"),
        ),
    "hers": (
            "3rd person",
            "female",
            "possessive pronoun"
        ),
    "herself": (
            "3rd person",
            "female",
            "reflexive pronoun"
        ),
    "it": (
            "3rd person",
            "neutral",
            ("subject pronoun", "object pronoun"),
        ),
    "its": (
            "3rd person",
            "neutral",
            ("possessive pronoun", "possessive adjective"),
        ),
    "itself": (
            "3rd person",
            "neutral",
            "reflexive pronoun"
        ),
    "they": (
            "3rd person",
            "plural",
            "subject pronoun"
        ),
    "them": (
            "3rd person",
            "plural",
            "object pronoun"
        ),
    "their": (
            "3rd person",
            "plural",
            "possessive adjective"
        ),
    "theirs": (
            "3rd person",
            "plural",
            "possessive pronoun"
        ),
    "themselves": (
            "3rd person",
            "plural",
            "reflexive pronoun"
        ),
}

# define the default viewpoint conversions
VIEWPOINT_CONVERSION = {
    "1st person": "3rd person",
    "2nd person": "3rd person",
    "3rd person": ("1st person", "2nd person"),
}

ALIASES = {
    "m": "male",
    "f": "female",
    "n": "neutral",
    "p": "plural",
    "1st": "1st person",
    "2nd": "2nd person",
    "3rd": "3rd person",
    "1": "1st person",
    "2": "2nd person",
    "3": "3rd person",
    "s": "subject pronoun",
    "sp": "subject pronoun",
    "subject": "subject pronoun",
    "op": "object pronoun",
    "object": "object pronoun",
    "pa": "possessive adjective",
    "pp": "possessive pronoun",
}


def pronoun_to_viewpoints(
    pronoun, options=None, pronoun_type=DEFAULT_PRONOUN_TYPE, gender=DEFAULT_GENDER, viewpoint=DEFAULT_VIEWPOINT
):
    """
    Access function for determining the forms of a pronount from different viewpoints.

    Args:
        pronoun (str): A valid English pronoun, such as 'you', 'his', 'themselves' etc.
        options (str or list, optional): A list or space-separated string of options to help
            the engine when there is no unique mapping to use. This could for example
            be "2nd female" (alias 'f') or "possessive adjective" (alias 'pa' or 'a').
        pronoun_type (str, optional): An explicit object pronoun to separate cases where
            there is no unique mapping. Pronoun types defined in `options` take precedence.
            Values are

            - `subject pronoun`/`subject`/`sp` (I, you, he, they)
            - `object pronoun`/`object/`/`op`  (me, you, him, them)
            - `possessive adjective`/`adjective`/`pa` (my, your, his, their)
            - `possessive pronoun`/`pronoun`/`pp` (mine, yours, his, theirs)

        gender (str, optional): Specific gender to use (plural counts a gender for this purpose).
            A gender specified in `options` takes precedence. Values and aliases are:

            - `male`/`m`
            - `female`/`f`
            - `neutral`/`n`
            - `plural`/`p`

        viewpoint (str, optional): A specified viewpoint of the one talking, to use
            when there is no unique mapping. A viewpoint given in `options` take
            precedence. Values and aliases are:

            - `1st person`/`1st`/`1`
            - `2nd person`/`2nd`/`2`
            - `3rd person`/`3rd`/`3`

    Returns:
        tuple: A tuple `(1st/2nd_person_pronoun, 3rd_person_pronoun)` to show to the one sending the
        string and others respectively. If pronoun is invalid, the word is returned verbatim.

    Note:
        The capitalization of the original word will be retained.

    """
    if not pronoun:
        return pronoun

    pronoun_lower = "I" if pronoun == "I" else pronoun.lower()

    if pronoun_lower not in PRONOUN_TABLE:
        return pronoun

    # get the default data for the input pronoun
    source_viewpoint, source_gender, source_type = PRONOUN_TABLE[pronoun_lower]

    # differentiators
    if pronoun_type not in PRONOUN_TYPES:
        pronoun_type = DEFAULT_PRONOUN_TYPE
    if viewpoint not in VIEWPOINTS:
        viewpoint = DEFAULT_VIEWPOINT
    if gender not in GENDERS:
        gender = DEFAULT_GENDER
    
    if options:
        # option string/list will override the kwargs differentiators given
        if isinstance(options, str):
            options = options.split()
        options = [str(part).strip().lower() for part in options]
        options = [ALIASES.get(opt, opt) for opt in options]

        for opt in options:
            if opt in PRONOUN_TYPES:
                pronoun_type = opt
            elif opt in VIEWPOINTS:
                viewpoint = opt
            elif opt in GENDERS:
                gender = opt

    # check if pronoun maps to multiple options and differentiate
    # but don't allow invalid differentiators
    if is_iter(source_type):
        pronoun_type = pronoun_type if pronoun_type in source_type else source_type[0]
    else:
        pronoun_type = source_type
    target_viewpoint = VIEWPOINT_CONVERSION[source_viewpoint]
    if is_iter(target_viewpoint):
        viewpoint = viewpoint if viewpoint in target_viewpoint else target_viewpoint[0]
    else:
        viewpoint = target_viewpoint

    # special handling for the royal "we"
    if is_iter(source_gender):
      gender_opts = list(source_gender)
    else:
      gender_opts = [source_gender]
    if viewpoint == "1st person":
        # make sure plural is always an option when converting to 1st person
        # it doesn't matter if it's in the list twice, so don't bother checking
        gender_opts.append("plural")
    # if the gender is still not in the extended options, fall back to source pronoun's default
    gender = gender if gender in gender_opts else gender_opts[0]

    # step down into the mapping
    viewpoint_map = PRONOUN_MAPPING[viewpoint]
    
    if pronoun_type in viewpoint_map:
        pronouns = viewpoint_map[pronoun_type]
    else:
        pronouns = viewpoint_map[DEFAULT_PRONOUN_TYPE]
    if gender in pronouns:
        mapped_pronoun = pronouns[gender]
    else:
        mapped_pronoun = pronouns[DEFAULT_GENDER]
    
    # keep the same capitalization as the original
    if pronoun != "I":
        # don't remap I, since this is always capitalized.
        mapped_pronoun = copy_word_case(pronoun, mapped_pronoun)
    if mapped_pronoun == "i":
        mapped_pronoun = mapped_pronoun.upper()

    if viewpoint == "3rd person":
        # the desired viewpoint is 3rd person, meaning the incoming viewpoint
        # must have been 1st or 2nd person.
        return pronoun, mapped_pronoun
    else:
        # the desired viewpoint is 1st or 2nd person, so incoming must have been
        # in 3rd person form.
        return mapped_pronoun, pronoun

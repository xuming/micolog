from django.template import Library
from django.template import Node, NodeList, Template, Context
from django.template import TemplateSyntaxError, VariableDoesNotExist, BLOCK_TAG_START, BLOCK_TAG_END, VARIABLE_TAG_START, VARIABLE_TAG_END, SINGLE_BRACE_START, SINGLE_BRACE_END, COMMENT_TAG_START, COMMENT_TAG_END

register = Library()

class RecurseNode( Node ):
    def __init__(self, **kwargs):
        self.loopvar, self.sequence = kwargs['loopvar'], kwargs['sequence']
        self.children_name  = kwargs['children_name']
        self.nodelist_first, self.nodelist_second = kwargs['nodelist_first'], kwargs['nodelist_second']
        del kwargs['nodelist_first'], kwargs['nodelist_second'], kwargs['sequence'], kwargs['children_name'], kwargs['loopvar']
        self.kwargs = kwargs
        
    def __repr__(self):
        reversed_text = self.is_reversed and ' reversed' or ''
        return "<For Node: for %s in %s, tail_len: %d%s>" % \
            (', '.join(self.loopvars), self.sequence, len(self.nodelist_loop),
             reversed_text)

    def __iter__(self):
      for node in self.nodelist_first:
        yield node
      for node in self.nodelist_second:
        yield node

    def get_nodes_by_type(self, nodetype):
      nodes = []
      if isinstance(self, nodetype):
        nodes.append(self)
      nodes.extend( self.nodelist_first.get_nodes_by_type(nodetype) )
      nodes.extend( self.nodelist_second.get_nodes_by_type(nodetype) )
      return nodes

    def render(self, context, depth=0, values=False):
        nodelist = NodeList()
        if 'recurseloop' in context:
            parentloop = context['recurseloop']
        else:
            parentloop = {}
        context.push()
        
        # On the first recursion pass, we have no values
        if not values:
          try:
              values = self.sequence.resolve(context, True)
          except VariableDoesNotExist:
              values = []
          if values is None:
              values = []
          if not hasattr(values, '__len__'):
              values = list(values)

        len_values = len(values)
        
        # Create a recurseloop value in the context.  We'll update counters on each iteration just below.
        loop_dict = context['recurseloop'] = {'parent': parentloop}
        
        loop_dict['depth'] = depth + 1
        loop_dict['depth0'] = depth

        for i, item in enumerate(values):
            # Add the additional arguments to the context
            # They come in the form of {'name':(initial,increment)}
            # As for now only numbers are supported, but also strings can be multiplied 
            for k,v in self.kwargs.iteritems():
              context[k] = v[0] + v[1]*depth
              
            # Shortcuts for current loop iteration number.
            loop_dict['counter0'] = i
            loop_dict['counter'] = i+1

            # Boolean values designating first and last times through loop.
            loop_dict['first'] = (i == 0)
            loop_dict['last'] = (i == len_values - 1)

            context[ self.loopvar ] = item
            
            for node in self.nodelist_first:
                nodelist.append( node.render(context) )
            
            if len( getattr( item, self.children_name ) ):
                nodelist.append( self.render( context, depth+1, getattr( item, self.children_name ) ) )
            
            for node in self.nodelist_second:
                nodelist.append( node.render(context) )
                        
        context.pop()
        return nodelist.render(context)

#@register.tag(name="for")
def do_recurse(parser, token):
    """
    Recursively loops over each item in an array . 
    It also increments passed variables on each recursion depth.
    For example, to display a list of comments with replies given ``comment_list``:
    
      {% recurse comment in comments children="replies" indent=(0,20) %}
          <div style="margin-left:{{indent}}px">{{ comment.text }}</div>
      {% endrecurse %}
    
    ``children`` is the name of the iterable that contains the children of the current element
    ``children`` needs to be a property of comment, and is required for the recurseloop to work
    You can pass additional parameters after children in the form of:
        
      var_name=(intial_value, increment)
    
    You need to take care of creating the tree structure on your own.
    As for now there should be no spaces between the equal ``=`` 
    signs when assigning children or additional variables
    
    In addition to the variables passed, the recurse loop sets a 
    number of variables available within the loop:
        ==========================  ================================================
        Variable                    Description
        ==========================  ================================================
        ``recurseloop.depth``       The current depth of the loop (1 is the top level)
        ``recurseloop.depth0``      The current depth of the loop (0 is the top level)
        ``recurseloop.counter``     The current iteration of the current level(1-indexed)
        ``recurseloop.counter0``    The current iteration of the current level(0-indexed)
        ``recurseloop.first``       True if this is the first time through the current level
        ``recurseloop.last``        True if this is the last time through the current level
        ``recurseloop.parent``      This is the loop one level "above" the current one
        ==========================  ================================================
    
    You can also use the tag {% yield %} inside a recursion.
    The ``yield`` tag will output the same HTML that's between the recurse and endrecurse tags
    if the current element has children. If there are no children ``yield`` will output nothing
    You must not, however wrap the ``yield`` tag inside other tags, just like you must not wrap
    the ``else`` tag inside other tags when making if-else-endif 
    """
    # We will be throwing this a lot
    def tError( contents ):
      raise TemplateSyntaxError(
      "'recurse' statements should use the format"
      "'{%% recurse x in y children=\"iterable_property_name\" "
      "arg1=(float,float) arg2=(\"str\",\"str\") %%}: %s" % contents )

    bits = token.contents.split()
    quotes = ["'","\""]
    lenbits = len(bits)
    if lenbits < 5:
        tError(token.contents)
        
    in_index = 2
    children_index = 4
    if bits[in_index] != 'in':
        tError(token.contents)
                                  
    children_token = bits[children_index].split("=")
    
    if len(children_token) != 2 or children_token[0] != 'children':
        tError(token.contents)

    f = children_token[1][0]
    l = children_token[1][-1]
    
    if f != l or f not in quotes:
        tError(token.contents)
    else:
      children_token[1] = children_token[1].replace(f,"")
    
    def convert(val):
      try:
        val = float(val)
      except ValueError:
        f = val[0]
        l = val[-1]
        if f != l or f not in quotes:
            tError(token.contents)
        val = unicode( val.replace(f,"") )
      return val

    node_vars = {}
    if lenbits > 5:
      for bit in bits[5:]:
        arg = bit.split("=")

        if len(arg) != 2 :
          tError(token.contents)

        f = arg[1][0]
        l = arg[1][-1]
        if f != "(" or l != ")":
            tError(token.contents)
        
        try:
          argval = tuple([ convert(x) for x in arg[1].replace("(","").replace(")","").split(",") ])
        # Invalid float number, or missing comma
        except (IndexError, ValueError):
            tError(token.contents)
        node_vars[ str(arg[0]) ] = argval
        
    node_vars['children_name'] = children_token[1]
    node_vars['loopvar'] = bits[1]
    node_vars['sequence'] = parser.compile_filter(bits[3])
    
    nodelist_first = parser.parse( ('yield', 'endrecurse',) )
    token = parser.next_token()
    if token.contents == 'yield':
      nodelist_second = parser.parse( ('endrecurse', ) )
      parser.delete_first_token()
    else:
      nodelist_second = NodeList()
    node_vars['nodelist_first'] = nodelist_first
    node_vars['nodelist_second'] = nodelist_second
    return RecurseNode(**node_vars)
do_recurse = register.tag("recurse", do_recurse)

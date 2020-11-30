import operator
import re



class SemVersion:
    """

    >>> SemVersion(1,2,3)
    <SemVersion ver='1.2.3'/>
    >>> SemVersion(1,2,3,"b32")
    <SemVersion ver='1.2.3b32'/>
    >>> SemVersion(1,2,3,"-1e36f22")
    <SemVersion ver='1.2.3-1e36f22'/>
    >>> SemVersion(1,2,3,"-1e36f22") == SemVersion(1,2,3,"a32")
    True
    >>> SemVersion(1,2,3) < SemVersion(1,3,2)
    True
    >>> SemVersion(1,2,3) < SemVersion(1,2,1)
    False
    >>> SemVersion(1,2,3) > SemVersion(1,2,1)
    True

    """
    version_re = re.compile("(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<build>\d+)(?P<extra>[^ \d][0-9a-zA-Z]*)?)?")
    @staticmethod
    def from_string(s):
        """
        >>> SemVersion.from_string("1.2.3")
        <SemVersion ver='1.2.3'/>
        >>> SemVersion.from_string("1.2.3-ac12ef6")
        <SemVersion ver='1.2.3-ac12ef6'/>

        :param s:
        :return:
        """
        match = SemVersion.version_re.search(s)
        if not match:
            raise TypeError("cannot parse %r to version"%(s,))
        return SemVersion(match.group('major'),match.group('minor'),match.group('build'),match.group("extra"))

    # def __lt__(self, other):
    #     return self.__cmp__("lt",other)
    # def __le__(self, other):
    #     return self.__cmp__("le",other)
    # def __ge__(self, other):
    #     return self.__cmp__("ge",other)
    # def __gt__(self, other):
    #     """
    #     :param other:
    #     :return:
    #     """
    #     return self.__cmp__("gt",other)
    def __init__(self,major,minor,build,extra=""):
        self.version_tuple = [0,0,0]
        self.extra_tag = ""
        self.__init_cmp()
        self.set(major,minor,build,extra)
    @property
    def major(self):
        return self.version_tuple[0]
    @property
    def minor(self):
        return self.version_tuple[1]

    @property
    def build(self):
        return self.version_tuple[2]
    def set(self,major=None,minor=None,build=None,extra=""):
        self.version_tuple = (int(major or self.version_tuple[0]),
                              int(minor or self.version_tuple[1]),
                              int(build or self.version_tuple[1]))
        self.extra_tag = extra or self.extra_tag
        self.version = "{0}.{1}.{2}{extra}".format(*self.version_tuple,extra=self.extra_tag)

    def __init_cmp(self):
        for c in ['lt','le','gt','ge']:
            def cmp_it(a=None,b=None,method=c):
                return a.__cmp__(method,b)
            setattr(self.__class__,'__%s__'%c,cmp_it)


    def __str__(self):
        return self.version
    def __repr__(self):
        return "<SemVersion ver='%s'/>"%(self,)
    def __eq__(self,other):
        """
        >>> SemVersion(1,2,3) == 1
        True
        >>> SemVersion(1,2,3) == [1,2]
        True
        >>> SemVersion(1,2,3) == [1,4]
        False
        >>> SemVersion(1,2,3) == 3
        False
        >>> SemVersion(1,2,3) != 3
        True
        """
        other = self.get_version_tuple_from_object(other)
        if isinstance(other,(list,tuple)):
            for a,b in zip(self.version_tuple,other):
                if a != b:
                    return False
            return True
        return self.__cmp__(other)
    def get_version_tuple_from_object(self,other):
        import six
        # print("CONVERT:",repr(other))
        if isinstance(other, (bytes, six.string_types)):
            other = [int(x) for x in other.split(".",4)[:3]]
        if isinstance(other, (list,tuple)):
            other = tuple(int(i) for i in other[:3])
        if isinstance(other,SemVersion):
            other = other.version_tuple
        if isinstance(other,int):
            other = (other,)
        return other
    def __cmp__(self,fn_name,other):
        """
        >>> s=SemVersion(1,2,3)
        >>> s == 1
        True
        >>> s > 1
        True
        >>> s > 2
        False
        >>> s > [1,2]
        True
        >>> s > [1,2,3]
        False
        >>> s < [1,2,3]
        False

        :param fn_name:
        :param other:
        :return:
        """
        # print(repr(self),repr(fn_name),repr(other))
        other = self.get_version_tuple_from_object(other)
        result = getattr(operator,fn_name)(self.version_tuple,other)
        # print("CMP:",fn_name,repr(self),repr(other),"=>",result)
        return result
        # if not isinstance(other,(list,tuple)):
        #     raise TypeError("Cannot Compare %r to %r"%(self,other))
        # if self.version_tuple == other:
        #     return 0
        # elif self.version_tuple < other:
        #     return -1
        # else:
        #     return 1
